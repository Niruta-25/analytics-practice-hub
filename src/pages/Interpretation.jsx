import { useState } from 'react';
import AiHelp from '../components/AiHelp.jsx';
import SelfRating from '../components/SelfRating.jsx';
import Timer from '../components/Timer.jsx';
import { regressionById, regressionExams, skillById } from '../lib/data.js';
import { go, href } from '../lib/router.js';

function RegressionQuestion({ question }) {
  const [revealed, setRevealed] = useState(false);
  return (
    <article className="question">
      <div className="chips">
        <span className="chip chip-regression">Regression</span>
        <span className="chip">{question.id}</span>
        <span className="chip">{skillById[question.skill].name}</span>
      </div>
      <h2 className="question-text">{question.text}</h2>
      <button className="btn" onClick={() => setRevealed((v) => !v)} aria-expanded={revealed}>
        {revealed ? 'Hide answer' : 'Show answer'}
      </button>
      {revealed && (
        <div className="answer">
          <h3>Expected answer</h3>
          <p>{question.answer}</p>
          <h3>What to say to the examiner</h3>
          <p>{question.say}</p>
          <SelfRating questionId={question.id} skill={question.skill} />
        </div>
      )}
      <AiHelp questionId={question.id} placeholder="Write your calculation or the explanation you would give" />
    </article>
  );
}

function RegressionRun({ exam }) {
  const [index, setIndex] = useState(0);
  return (
    <>
      <a className="back" href={href('interpretation')}>← All interpretation exams</a>
      <p className="eyebrow">DATA INTERPRETATION EXAM · {exam.id} · {exam.minutes} MINUTES</p>
      <h1>{exam.title}</h1>
      <p className="lead">
        Bob owns a restaurant and wants to plan ingredients and staff. The model below was fitted
        on his daily data for 2018.
      </p>

      <Timer key={exam.id} minutes={exam.minutes} note="The five minutes cover all four questions." />

      <section className="model">
        <h2 className="section-title">The model</h2>
        <p><strong>Dependent variable:</strong> {exam.dependent}</p>
        <dl className="variables">
          {exam.variables.map((v) => (
            <div key={v.name}>
              <dt>{v.name}</dt>
              <dd>{v.unit}{v.range ? ` · typical range ${v.range}` : ''}</dd>
            </div>
          ))}
        </dl>
        <p className="equation">{exam.equation}</p>
        <table>
          <caption>Regression output · R-squared {exam.r2.toFixed(3)} · {exam.n} observations</caption>
          <thead>
            <tr><th>Parameter</th><th>Term</th><th>Estimate</th><th>p-value</th></tr>
          </thead>
          <tbody>
            {exam.output.map((row, i) => (
              <tr key={row.term}>
                <td>b{i}</td>
                <td>{row.term}</td>
                <td className="number">{row.estimate.toLocaleString('en-US', { maximumFractionDigits: 4 })}</td>
                <td className="number">{row.p}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="tabs" role="tablist">
        {exam.questions.map((q, i) => (
          <button key={q.id} role="tab" aria-selected={i === index} className={i === index ? 'active' : ''} onClick={() => setIndex(i)}>
            Question {i + 1}
          </button>
        ))}
      </div>
      <RegressionQuestion key={exam.questions[index].id} question={exam.questions[index]} />
      <div className="pager">
        <button className="btn" disabled={index === 0} onClick={() => setIndex(index - 1)}>← Previous question</button>
        <button className="btn" disabled={index === exam.questions.length - 1} onClick={() => setIndex(index + 1)}>Next question →</button>
      </div>
    </>
  );
}

export default function Interpretation({ id }) {
  if (id) {
    const exam = regressionById[id];
    return (
      <main className="page">
        {exam ? <RegressionRun key={exam.id} exam={exam} /> : <p>Exam {id} was not found. <a href={href('interpretation')}>Back to all exams</a></p>}
      </main>
    );
  }
  const pickRandom = () => go('interpretation', regressionExams[Math.floor(Math.random() * regressionExams.length)].id);
  return (
    <main className="page">
      <p className="eyebrow">DATA INTERPRETATION</p>
      <h1>Regression exams</h1>
      <p className="lead">
        Each exam shows one regression fitted on the restaurant case data and asks four questions about it.
        You have five minutes.
      </p>
      <button className="btn btn-primary btn-large" onClick={pickRandom}>Choose one for me</button>

      <h2 className="section-title">All {regressionExams.length} exams</h2>
      <ul className="rows">
        {regressionExams.map((exam) => (
          <li key={exam.id}>
            <a href={href('interpretation', exam.id)}>
              <span className="row-id">{exam.id}</span>
              <span className="row-main">
                <strong>{exam.title}</strong>
                <span className="muted">{exam.questions.map((q) => skillById[q.skill].name).join(' · ')}</span>
              </span>
              <span className="chip">{exam.minutes} min</span>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
