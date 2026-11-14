import { regressionExams, skills } from '../lib/data.js';
import { STATUS, bestRegressionExam, clearProgress, nextQuestionFor, summarise, useAttempts } from '../lib/progress.js';
import { href } from '../lib/router.js';

const SUBJECTS = ['Excel', 'SQL', 'Regression'];

// A regression exam that contains this skill, preferring a question not yet tried.
function regressionExamFor(skillId, tried) {
  const withSkill = regressionExams.filter((e) => e.questions.some((q) => q.skill === skillId));
  return withSkill.find((e) => e.questions.some((q) => q.skill === skillId && !tried.has(q.id))) || withSkill[0];
}

function ago(time) {
  const days = Math.floor((Date.now() - time) / 86400000);
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

export default function Coverage() {
  const attempts = useAttempts();
  const summary = summarise(attempts);
  const count = (status) => skills.filter((s) => summary.perSkill[s.id].status === status).length;
  const untouched = count('none');
  const regression = bestRegressionExam(summary);

  const reset = () => {
    if (window.confirm('Clear your skill coverage on this device? This cannot be undone.')) clearProgress();
  };

  return (
    <main className="page">
      <p className="eyebrow">YOUR PREPARATION</p>
      <h1>Skill coverage</h1>
      <p className="lead">
        The exam draws on {skills.length} skills. This map shows which ones you have practised and
        how they went, so you can spend your time on what you have not yet covered.
      </p>

      <div className="coverage-summary">
        <div><strong>{count('secure')}</strong><span>Secure</span></div>
        <div><strong>{count('started')}</strong><span>Started</span></div>
        <div><strong>{count('weak')}</strong><span>Needs work</span></div>
        <div className={untouched ? 'alert' : ''}><strong>{untouched}</strong><span>Not practised</span></div>
      </div>

      {attempts.length === 0 ? (
        <p className="notice">
          Nothing recorded yet. Open any question, press “Show answer”, and say how it went. Your map fills in from there.
        </p>
      ) : (
        <p className="notice">
          {untouched > 0
            ? `${untouched} of the ${skills.length} skills could come up in the exam without you having practised them once.`
            : 'You have practised every skill at least once. Keep going until each one is secure.'}
        </p>
      )}

      <div className="card-actions">
        <a className="btn btn-primary btn-large" href={href('exams', 'gaps')}>Build an exam from my gaps</a>
        {regression && <a className="btn btn-large" href={href('interpretation', regression.id)}>Regression exam for my gaps</a>}
      </div>

      {SUBJECTS.map((subject) => (
        <section key={subject}>
          <h2 className="section-title">{subject}</h2>
          <ul className="skills">
            {skills.filter((s) => s.subject === subject).map((skill) => {
              const info = summary.perSkill[skill.id];
              const next = subject === 'Regression' ? null : nextQuestionFor(skill.id, summary);
              return (
                <li key={skill.id} className={`skill skill-${info.status}`}>
                  <div className="skill-main">
                    <strong>{skill.name}</strong>
                    <span className="muted">{skill.description}</span>
                  </div>
                  <div className="skill-state">
                    <span className={`status status-${info.status}`}>{STATUS[info.status].label}</span>
                    <span className="muted">
                      {info.questionsTried} of {info.questionsTotal} questions tried
                      {info.last ? ` · last ${ago(info.last)}` : ''}
                    </span>
                  </div>
                  {next ? (
                    <a className="btn" href={href('questions', next.id)}>Practise</a>
                  ) : (
                    <a className="btn" href={href('interpretation', regressionExamFor(skill.id, summary.tried).id)}>Practise</a>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      <p className="muted privacy">
        Your coverage is stored only in this browser on this device. It is never sent anywhere, and clearing
        your browser data removes it. A skill counts as secure after two “Got it” results in a row.
      </p>
      <button className="btn" onClick={reset} disabled={attempts.length === 0}>Clear my coverage</button>
    </main>
  );
}
