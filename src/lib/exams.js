// Builds the data manipulation exams from the question bank.
//
// The real exam gives one Excel file and one database, with Excel questions
// followed by SQL questions, to be solved in about eight minutes. Each practice
// exam follows that shape: three Excel questions on one file and two SQL
// questions on one database. A fixed seed means every student sees the same
// exam under the same number, so "E017" can be discussed in class.
import { questions } from './data.js';

const EXCEL_PER_EXAM = 3;
const SQL_PER_EXAM = 2;
const EXAM_COUNT = 60;
export const EXAM_MINUTES = 8;

function seededRandom(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffled(list, random) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// Prefer questions that train different skills, so one exam covers more ground.
function pickVaried(pool, count, random) {
  const picked = [];
  const usedSkills = new Set();
  const order = shuffled(pool, random);
  for (const q of order) {
    if (picked.length < count && !usedSkills.has(q.skill)) {
      picked.push(q);
      usedSkills.add(q.skill);
    }
  }
  for (const q of order) {
    if (picked.length < count && !picked.includes(q)) picked.push(q);
  }
  return picked;
}

function byDataset(subject) {
  const groups = {};
  for (const q of questions) {
    if (q.subject === subject) (groups[q.dataset] ||= []).push(q);
  }
  return groups;
}

function buildExams() {
  const excel = byDataset('Excel');
  const sql = byDataset('SQL');
  const excelKeys = Object.keys(excel).filter((k) => excel[k].length >= EXCEL_PER_EXAM);
  const sqlKeys = Object.keys(sql).filter((k) => sql[k].length >= SQL_PER_EXAM);
  const random = seededRandom(20261114);
  const exams = [];
  const seen = new Set();
  // Go round every pairing of an Excel file with a database, so no file dominates.
  const pairs = [];
  for (const excelKey of excelKeys) for (const sqlKey of sqlKeys) pairs.push([excelKey, sqlKey]);
  let round = 0;
  while (exams.length < EXAM_COUNT && round < 10) {
    round += 1;
    for (const [excelKey, sqlKey] of shuffled(pairs, random)) {
      if (exams.length >= EXAM_COUNT) break;
      // Of several varied draws, keep the one whose estimated time is closest to the exam length.
      let best = null;
      for (let draw = 0; draw < 25; draw += 1) {
        const picked = [
          ...pickVaried(excel[excelKey], EXCEL_PER_EXAM, random),
          ...pickVaried(sql[sqlKey], SQL_PER_EXAM, random),
        ];
        const signature = picked.map((q) => q.id).sort().join('|');
        if (seen.has(signature)) continue;
        const gap = Math.abs(picked.reduce((sum, q) => sum + q.minutes, 0) - EXAM_MINUTES);
        if (!best || gap < best.gap) best = { picked, signature, gap };
      }
      if (!best || best.gap > 2) continue;
      seen.add(best.signature);
      // Import comes first in a real sitting: nothing else works until the file is loaded.
      best.picked.sort((x, y) => Number(y.skill === 'xl-import') - Number(x.skill === 'xl-import'));
      exams.push({
        id: `E${String(exams.length + 1).padStart(3, '0')}`,
        excelDataset: excelKey,
        sqlDataset: sqlKey,
        questionIds: best.picked.map((q) => q.id),
      });
    }
  }
  return exams;
}

export const exams = buildExams();
export const examById = Object.fromEntries(exams.map((e) => [e.id, e]));
