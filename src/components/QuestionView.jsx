import { useState } from 'react';
import { datasets, formatMinutes, skillById } from '../lib/data.js';
import AiHelp from './AiHelp.jsx';
import DatasetFiles from './DatasetFiles.jsx';
import SelfRating from './SelfRating.jsx';

// Put each main clause of a model query on its own line so it can be read aloud.
function layoutSql(sql) {
  return sql.replace(/ (FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT|JOIN) /g, '\n$1 ');
}

// One Excel or SQL question with its answer hidden until the student asks for it.
// Render it with key={question.id} so the answer is hidden again for the next question.
export default function QuestionView({ question, showFiles = true }) {
  const [revealed, setRevealed] = useState(false);
  const skill = skillById[question.skill];

  return (
    <article className="question">
      <div className="chips">
        <span className={`chip chip-${question.subject.toLowerCase()}`}>{question.subject}</span>
        <span className="chip">{question.id}</span>
        <span className="chip">{skill.name}</span>
        <span className="chip">{formatMinutes(question.minutes)} estimated</span>
      </div>
      <h2 className="question-text">{question.text}</h2>
      <p className="muted">Data: {datasets[question.dataset].name}</p>
      {showFiles && <DatasetFiles keys={[question.dataset]} />}

      <button className="btn" onClick={() => setRevealed((v) => !v)} aria-expanded={revealed}>
        {revealed ? 'Hide answer' : 'Show answer'}
      </button>
      {revealed && (
        <div className="answer">
          <h3>Expected result</h3>
          <p>{question.answer}</p>
          <h3>{question.sql ? 'Model query' : 'How to get there'}</h3>
          {question.sql ? <pre><code>{layoutSql(question.sql)}</code></pre> : <p>{question.method}</p>}
          {question.sql && <p className="muted">{question.method}</p>}
          <SelfRating questionId={question.id} skill={question.skill} />
        </div>
      )}
      <AiHelp
        questionId={question.id}
        placeholder={question.sql ? 'Paste your SQL query or describe your approach' : 'Paste your formula or describe the steps you took'}
      />
    </article>
  );
}
