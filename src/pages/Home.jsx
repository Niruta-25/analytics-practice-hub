import { questions, regressionExams, skills } from '../lib/data.js';
import { exams } from '../lib/exams.js';
import { href } from '../lib/router.js';

export default function Home() {
  return (
    <>
      <header className="hero">
        <p className="eyebrow">DATA ANALYTICS IN ACCOUNTING</p>
        <h1>Practise the exam before you sit it.</h1>
        <p className="lead">
          The oral exam gives you one data manipulation exam and one data interpretation exam.
          Every question here is built from the course cases and has a checked answer.
        </p>
        <a className="btn btn-primary btn-large" href={href('exams')}>Start a practice exam</a>
      </header>

      <main className="page">
        <section className="cards">
          <div className="card">
            <p className="eyebrow">PART 1</p>
            <h2>Data manipulation</h2>
            <p>
              Three Excel questions on one data file and two SQL questions on one database,
              in eight minutes. Practise full exams or single questions.
            </p>
            <p className="count">{exams.length} exams · {questions.length} questions</p>
            <div className="card-actions">
              <a className="btn btn-primary" href={href('exams')}>Exams</a>
              <a className="btn" href={href('questions')}>Question bank</a>
            </div>
          </div>
          <div className="card">
            <p className="eyebrow">PART 2</p>
            <h2>Data interpretation</h2>
            <p>
              Read a regression output from the restaurant case, make a prediction and explain
              the results in plain language. Four questions in five minutes.
            </p>
            <p className="count">{regressionExams.length} exams · {regressionExams.length * 4} questions</p>
            <div className="card-actions">
              <a className="btn btn-primary" href={href('interpretation')}>Exams</a>
            </div>
          </div>
        </section>
        <section className="card coverage-card">
          <p className="eyebrow">YOUR PREPARATION</p>
          <h2>Skill coverage</h2>
          <p>
            The exam draws on {skills.length} skills across Excel, SQL and regression. Rate yourself after each
            answer and see which skills you have secured, which need work, and which you have not touched.
          </p>
          <div className="card-actions">
            <a className="btn btn-primary" href={href('coverage')}>See my coverage</a>
            <a className="btn" href={href('exams', 'gaps')}>Exam from my gaps</a>
          </div>
        </section>
      </main>
    </>
  );
}
