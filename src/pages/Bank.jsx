import { useMemo, useState } from 'react';
import QuestionView from '../components/QuestionView.jsx';
import { datasets, questionById, questions, skillById, skills } from '../lib/data.js';
import { go, href } from '../lib/router.js';

const PAGE_SIZE = 20;

function QuestionPage({ id }) {
  const question = questionById[id];
  if (!question) return <p>Question {id} was not found. <a href={href('questions')}>Back to the question bank</a></p>;
  const index = questions.indexOf(question);
  return (
    <>
      <a className="back" href={href('questions')}>← Question bank</a>
      <QuestionView key={question.id} question={question} />
      <div className="pager">
        <button className="btn" disabled={index === 0} onClick={() => go('questions', questions[index - 1].id)}>
          ← Previous
        </button>
        <button className="btn" disabled={index === questions.length - 1} onClick={() => go('questions', questions[index + 1].id)}>
          Next →
        </button>
      </div>
    </>
  );
}

export default function Bank({ id }) {
  const [subject, setSubject] = useState('');
  const [dataset, setDataset] = useState('');
  const [skill, setSkill] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return questions.filter(
      (q) =>
        (!subject || q.subject === subject) &&
        (!dataset || q.dataset === dataset) &&
        (!skill || q.skill === skill) &&
        (!needle || q.text.toLowerCase().includes(needle) || q.id.toLowerCase().includes(needle)),
    );
  }, [subject, dataset, skill, search]);

  if (id) return <main className="page"><QuestionPage id={id} /></main>;

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const visible = filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);
  const change = (setter) => (event) => {
    setter(event.target.value);
    setPage(0);
  };
  const manipulationSkills = skills.filter((s) => s.subject !== 'Regression' && (!subject || s.subject === subject));

  return (
    <main className="page">
      <p className="eyebrow">DATA MANIPULATION</p>
      <h1>Question bank</h1>
      <p className="lead">Every question that can appear in a data manipulation exam.</p>

      <div className="filters">
        <label>
          Subject
          <select value={subject} onChange={(e) => { setSubject(e.target.value); setSkill(''); setPage(0); }}>
            <option value="">All subjects</option>
            <option>Excel</option>
            <option>SQL</option>
          </select>
        </label>
        <label>
          Data file
          <select value={dataset} onChange={change(setDataset)}>
            <option value="">All files</option>
            {Object.entries(datasets).map(([key, d]) => <option key={key} value={key}>{d.name}</option>)}
          </select>
        </label>
        <label>
          Skill
          <select value={skill} onChange={change(setSkill)}>
            <option value="">All skills</option>
            {manipulationSkills.map((s) => <option key={s.id} value={s.id}>{s.subject}: {s.name}</option>)}
          </select>
        </label>
        <label>
          Find
          <input type="search" value={search} onChange={change(setSearch)} placeholder="Word or question number" />
        </label>
      </div>

      <p className="muted" role="status">{filtered.length} of {questions.length} questions</p>
      <ul className="rows">
        {visible.map((q) => (
          <li key={q.id}>
            <a href={href('questions', q.id)}>
              <span className="row-id">{q.id}</span>
              <span className="row-main">
                <strong>{q.text}</strong>
                <span className="muted">{datasets[q.dataset].name} · {skillById[q.skill].name}</span>
              </span>
              <span className={`chip chip-${q.subject.toLowerCase()}`}>{q.subject}</span>
            </a>
          </li>
        ))}
      </ul>
      {filtered.length === 0 && <p>No questions match these filters.</p>}

      <div className="pager">
        <button className="btn" disabled={current === 0} onClick={() => setPage(current - 1)}>← Previous</button>
        <span className="muted">Page {current + 1} of {pages}</span>
        <button className="btn" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>Next →</button>
      </div>
    </main>
  );
}
