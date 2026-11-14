import { useState } from 'react';
import DatasetFiles from '../components/DatasetFiles.jsx';
import QuestionView from '../components/QuestionView.jsx';
import Timer from '../components/Timer.jsx';
import { datasets, questionById, skillById } from '../lib/data.js';
import { buildGapExam, gapsInExam, summarise, useAttempts } from '../lib/progress.js';
import { EXAM_MINUTES, examById, exams } from '../lib/exams.js';
import { go, href } from '../lib/router.js';

function ExamRun({ exam }) {
  const [index, setIndex] = useState(0);
  const list = exam.questionIds.map((qid) => questionById[qid]);
  const question = list[index];
  return (
    <>
      <a className="back" href={href(exam.id === 'gaps' ? 'coverage' : 'exams')}>
        {exam.id === 'gaps' ? '← Skill coverage' : '← All exams'}
      </a>
      <p className="eyebrow">DATA MANIPULATION EXAM · {EXAM_MINUTES} MINUTES</p>
      <h1>{exam.id === 'gaps' ? 'Exam built from your gaps' : `Exam ${exam.id}`}</h1>
      {exam.id === 'gaps' && (
        <p className="lead">
          Same format as the real exam, with questions chosen for the skills you have not secured yet:{' '}
          {[...new Set(list.map((q) => skillById[q.skill].name))].join(', ')}.
        </p>
      )}

      <h2 className="section-title">Files for this exam</h2>
      <DatasetFiles keys={[exam.excelDataset, exam.sqlDataset]} />

      <Timer
        key={exam.id}
        minutes={EXAM_MINUTES}
        note="Download and open the files before you start the timer. Importing the data is part of the timed exam."
      />

      <div className="exam-layout">
        <nav className="exam-nav" aria-label="Exam questions">
          {list.map((q, i) => (
            <button key={q.id} className={i === index ? 'active' : ''} onClick={() => setIndex(i)} aria-current={i === index}>
              <span>{i + 1}</span> {q.subject}
            </button>
          ))}
        </nav>
        <div>
          <QuestionView key={question.id} question={question} showFiles={false} />
          <div className="pager">
            <button className="btn" disabled={index === 0} onClick={() => setIndex(index - 1)}>← Previous question</button>
            <button className="btn" disabled={index === list.length - 1} onClick={() => setIndex(index + 1)}>Next question →</button>
          </div>
        </div>
      </div>
    </>
  );
}

// Built once when the page opens, so it does not reshuffle while the student rates answers.
function GapExam() {
  const attempts = useAttempts();
  const [exam] = useState(() => buildGapExam(summarise(attempts)));
  return <ExamRun exam={exam} />;
}

export default function Exams({ id }) {
  const attempts = useAttempts();
  if (id === 'gaps') return <main className="page"><GapExam /></main>;
  if (id) {
    const exam = examById[id];
    return (
      <main className="page">
        {exam ? <ExamRun key={exam.id} exam={exam} /> : <p>Exam {id} was not found. <a href={href('exams')}>Back to all exams</a></p>}
      </main>
    );
  }
  const summary = summarise(attempts);
  const pickRandom = () => go('exams', exams[Math.floor(Math.random() * exams.length)].id);
  return (
    <main className="page">
      <p className="eyebrow">DATA MANIPULATION</p>
      <h1>Practice exams</h1>
      <p className="lead">
        Each exam has three Excel questions on one data file and two SQL questions on one database.
        You have {EXAM_MINUTES} minutes.
      </p>
      <div className="card-actions">
        <button className="btn btn-primary btn-large" onClick={pickRandom}>Choose one for me</button>
        <a className="btn btn-large" href={href('exams', 'gaps')}>Build one from my gaps</a>
      </div>

      <h2 className="section-title">All {exams.length} exams</h2>
      <ul className="rows">
        {exams.map((exam) => (
          <li key={exam.id}>
            <a href={href('exams', exam.id)}>
              <span className="row-id">{exam.id}</span>
              <span className="row-main">
                <strong>{datasets[exam.excelDataset].name} + {datasets[exam.sqlDataset].name}</strong>
                <span className="muted">Excel file and SQL database</span>
              </span>
              {attempts.length > 0 && gapsInExam(exam.questionIds, summary) > 0 && (
                <span className="chip chip-gap">covers {gapsInExam(exam.questionIds, summary)} of your gaps</span>
              )}
              <span className="chip">{EXAM_MINUTES} min</span>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
