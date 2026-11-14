// One place that loads the question bank and indexes it for the pages.
import skillList from '../data/skills.json';
import datasets from '../data/datasets.json';
import questions from '../data/questions.json';
import regressionExams from '../data/regression.json';

export { datasets, questions, regressionExams };

export const skills = skillList;
export const skillById = Object.fromEntries(skillList.map((s) => [s.id, s]));
export const questionById = Object.fromEntries(questions.map((q) => [q.id, q]));
export const regressionById = Object.fromEntries(regressionExams.map((e) => [e.id, e]));

export function formatBytes(bytes) {
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(bytes >= 1e7 ? 0 : 1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1e3))} KB`;
}

export function formatMinutes(minutes) {
  const whole = Math.floor(minutes);
  const seconds = Math.round((minutes - whole) * 60);
  return `${whole}:${String(seconds).padStart(2, '0')}`;
}
