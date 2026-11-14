// Skill coverage: remembers how the student rated each question they practised
// and turns that into a status per skill.
//
// Everything is kept in this browser only (localStorage). Nothing is sent to a
// server and there are no accounts, so the site still knows nothing about who
// its students are.
import { useSyncExternalStore } from 'react';
import { questionById, questions, regressionExams, skills } from './data.js';

const KEY = 'analyticshub.progress.v1';
const MAX_ATTEMPTS = 3000;
export const RATINGS = [
  ['got', 'Got it'],
  ['partly', 'Partly'],
  ['missed', 'Missed it'],
];

let cache = null;
const listeners = new Set();

function load() {
  if (cache) return cache;
  try {
    const stored = JSON.parse(window.localStorage.getItem(KEY));
    cache = Array.isArray(stored) ? stored : [];
  } catch {
    cache = []; // storage blocked or corrupted: coverage works for this visit only
  }
  return cache;
}

function save(next) {
  cache = next;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Keep going with the in-memory copy.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// Each attempt: { q: question id, s: skill id, r: rating, t: time }
export function recordAttempt(questionId, skill, rating) {
  save([...load(), { q: questionId, s: skill, r: rating, t: Date.now() }].slice(-MAX_ATTEMPTS));
}

export function clearProgress() {
  save([]);
}

export function useAttempts() {
  return useSyncExternalStore(subscribe, load);
}

export const STATUS = {
  none: { label: 'Not practised', need: 3 },
  weak: { label: 'Needs work', need: 3 },
  started: { label: 'Started', need: 1 },
  secure: { label: 'Secure', need: 0 },
};

// A skill is secure after two "Got it" results in a row, on any of its questions.
// One good result is a start; a recent miss means it still needs work.
function statusOf(ratings) {
  if (ratings.length === 0) return 'none';
  const lastTwo = ratings.slice(-2);
  if (lastTwo.length === 2 && lastTwo.every((r) => r === 'got')) return 'secure';
  if (ratings[ratings.length - 1] === 'got') return 'started';
  return 'weak';
}

const questionsPerSkill = {};
for (const q of questions) questionsPerSkill[q.skill] = (questionsPerSkill[q.skill] || 0) + 1;
for (const exam of regressionExams) {
  for (const q of exam.questions) questionsPerSkill[q.skill] = (questionsPerSkill[q.skill] || 0) + 1;
}

export function summarise(attempts) {
  const bySkill = {};
  const tried = new Set();
  for (const a of attempts) {
    (bySkill[a.s] ||= []).push(a);
    tried.add(a.q);
  }
  const perSkill = {};
  for (const skill of skills) {
    const list = bySkill[skill.id] || [];
    perSkill[skill.id] = {
      status: statusOf(list.map((a) => a.r)),
      attempts: list.length,
      questionsTried: new Set(list.map((a) => a.q)).size,
      questionsTotal: questionsPerSkill[skill.id] || 0,
      last: list.length ? list[list.length - 1].t : null,
    };
  }
  return { perSkill, tried };
}

export function need(summary, skillId) {
  return STATUS[summary.perSkill[skillId].status].need;
}

// The question to do next for one skill: one not yet tried if possible.
export function nextQuestionFor(skillId, summary) {
  const pool = questions.filter((q) => q.skill === skillId);
  return pool.find((q) => !summary.tried.has(q.id)) || pool[0] || null;
}

// Builds a manipulation exam in the real format (three Excel questions on one
// file, two SQL questions on one database) aimed at the student's gaps.
export function buildGapExam(summary) {
  const groups = { Excel: {}, SQL: {} };
  for (const q of questions) (groups[q.subject][q.dataset] ||= []).push(q);

  const shuffle = (list) => {
    const copy = [...list];
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  };

  // Highest need first, then questions not yet tried; the shuffle varies equal candidates.
  const best = (pool, count) => {
    const ranked = shuffle(pool).sort(
      (a, b) =>
        need(summary, b.skill) - need(summary, a.skill) ||
        Number(summary.tried.has(a.id)) - Number(summary.tried.has(b.id)),
    );
    const picked = [];
    const used = new Set();
    for (const q of ranked) {
      if (picked.length < count && !used.has(q.skill)) {
        picked.push(q);
        used.add(q.skill);
      }
    }
    for (const q of ranked) if (picked.length < count && !picked.includes(q)) picked.push(q);
    return { picked, score: picked.reduce((sum, q) => sum + need(summary, q.skill), 0) };
  };

  const choose = (subject, count) => {
    let top = null;
    for (const [dataset, pool] of shuffle(Object.entries(groups[subject]))) {
      if (pool.length < count) continue;
      const candidate = { dataset, ...best(pool, count) };
      if (!top || candidate.score > top.score) top = candidate;
    }
    return top;
  };

  const excel = choose('Excel', 3);
  const sql = choose('SQL', 2);
  const picked = [...excel.picked, ...sql.picked];
  picked.sort((a, b) => Number(b.skill === 'xl-import') - Number(a.skill === 'xl-import'));
  return {
    id: 'gaps',
    excelDataset: excel.dataset,
    sqlDataset: sql.dataset,
    questionIds: picked.map((q) => q.id),
    gapSkills: picked.filter((q) => need(summary, q.skill) > 1).length,
  };
}

// How many of an exam's questions train a skill the student still needs.
export function gapsInExam(questionIds, summary) {
  const skillsHit = new Set(questionIds.map((id) => questionById[id].skill).filter((s) => need(summary, s) > 1));
  return skillsHit.size;
}

// The regression exam that covers the most skills the student still needs.
export function bestRegressionExam(summary) {
  let top = null;
  for (const exam of regressionExams) {
    const score = exam.questions.reduce((sum, q) => sum + need(summary, q.skill), 0);
    if (!top || score > top.score) top = { exam, score };
  }
  return top && top.score > 0 ? top.exam : null;
}
