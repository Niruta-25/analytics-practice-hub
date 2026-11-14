// Cloudflare Worker: serves the built site and answers POST /api/help.
//
// The Gemini API key lives only here, as the secret GEMINI_API_KEY. The browser
// never sees it. The browser sends a question number and the student's attempt;
// the question text and its checked answer are looked up on the server, so the
// tutor cannot be pointed at anything other than the course questions.
import datasets from '../src/data/datasets.json';
import questions from '../src/data/questions.json';
import regressionExams from '../src/data/regression.json';
import skills from '../src/data/skills.json';

const MAX_ATTEMPT = 3000;
const MAX_PROBLEM = 1500;
const DEFAULT_MODEL = 'gemini-3.5-flash';

const skillName = Object.fromEntries(skills.map((s) => [s.id, s.name]));
const bank = new Map(questions.map((q) => [q.id, q]));
for (const exam of regressionExams) {
  for (const q of exam.questions) bank.set(q.id, { ...q, exam });
}

const TUTOR_RULES = `You are a tutor for university students preparing for an oral exam in Data Analytics in Accounting. In the exam they solve Excel and SQL tasks and interpret regression output while explaining their reasoning aloud to an examiner.

How to help:
- Start from what the student wrote. Say what is right in it, then name the first thing that is wrong or missing.
- Give the next step, not the whole solution. Do not write out the complete formula or query unless the student's attempt is already nearly complete and only a small correction is left.
- If the student wrote nothing useful, ask what they would try first and give one pointer to the relevant Excel feature, SQL clause or regression concept.
- Use the real column, table and variable names given below.
- Never reveal the expected result as a number or list. The student can press "Show answer" when ready.
- Finish with one short sentence on how to explain this step aloud to the examiner.
- Plain text only, no Markdown symbols. At most 150 words.
- Only help with this question. If asked about anything else, say you can only help with the question on screen.`;

function describe(question) {
  if (question.exam) {
    const exam = question.exam;
    const rows = exam.output.map((r, i) => `b${i} ${r.term}: estimate ${r.estimate}, p-value ${r.p}`).join('\n');
    const variables = exam.variables.map((v) => `${v.name}: ${v.unit}`).join('\n');
    return `Regression question (skill: ${skillName[question.skill]}).
Dependent variable: ${exam.dependent}
${exam.equation}
Variables:
${variables}
Output (R-squared ${exam.r2}, ${exam.n} observations):
${rows}

Question: ${question.text}
Expected answer, for your eyes only: ${question.answer}`;
  }
  const data = datasets[question.dataset];
  return `${question.subject} question (skill: ${skillName[question.skill]}).
Data: ${data.name}. ${data.schema}

Question: ${question.text}
Expected result, for your eyes only: ${question.answer}
${question.sql ? `One correct query, for your eyes only: ${question.sql}` : `One correct method, for your eyes only: ${question.method}`}`;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });
}

async function help(request, env) {
  if (request.method !== 'POST') return json({ error: 'Use POST.' }, 405);
  if (!env.GEMINI_API_KEY) return json({ error: 'AI help is not set up on this site yet.' }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'The request could not be read.' }, 400);
  }
  const question = bank.get(String(body.questionId || ''));
  const attempt = String(body.attempt || '').trim();
  const problem = String(body.problem || '').trim();
  if (!question) return json({ error: 'Unknown question.' }, 400);
  if (!attempt) return json({ error: 'Write what you have tried first, even if it is only a first idea.' }, 400);
  if (attempt.length > MAX_ATTEMPT || problem.length > MAX_PROBLEM) {
    return json({ error: 'That is too long. Shorten your attempt and try again.' }, 400);
  }

  const model = env.GEMINI_MODEL || DEFAULT_MODEL;
  let upstream;
  try {
    upstream = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: `${TUTOR_RULES}\n\n${describe(question)}` }] },
        contents: [
          {
            role: 'user',
            parts: [{ text: `What I have so far:\n${attempt}\n\nWhat happens or where I am stuck:\n${problem || '(not stated)'}` }],
          },
        ],
        generationConfig: { temperature: 0.3, maxOutputTokens: 2048 },
      }),
    });
  } catch {
    return json({ error: 'The AI service could not be reached. Try again in a moment.' }, 502);
  }

  if (upstream.status === 429) return json({ error: 'The AI help has reached its usage limit for now. Try again in a minute.' }, 429);
  if (!upstream.ok) {
    console.error('Gemini error', upstream.status, (await upstream.text()).slice(0, 300));
    return json({ error: 'The AI service returned an error. Try again in a moment.' }, 502);
  }
  const data = await upstream.json();
  const candidate = data.candidates && data.candidates[0];
  const text = ((candidate && candidate.content && candidate.content.parts) || []).map((p) => p.text || '').join('').trim();
  if (!text) return json({ error: 'The AI gave no usable reply. Rephrase your attempt and try again.' }, 502);
  return json({ reply: text, cutOff: candidate.finishReason === 'MAX_TOKENS' });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/help') return help(request, env);
    if (url.pathname.startsWith('/api/')) return json({ error: 'Not found.' }, 404);
    return env.ASSETS.fetch(request);
  },
};
