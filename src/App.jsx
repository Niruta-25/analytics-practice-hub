import './App.css';
import { href, useRoute } from './lib/router.js';
import Bank from './pages/Bank.jsx';
import Coverage from './pages/Coverage.jsx';
import Exams from './pages/Exams.jsx';
import Home from './pages/Home.jsx';
import Interpretation from './pages/Interpretation.jsx';

const NAV = [
  ['exams', 'Manipulation exams'],
  ['questions', 'Question bank'],
  ['interpretation', 'Interpretation exams'],
  ['coverage', 'Skill coverage'],
];

export default function App() {
  const [section, id] = useRoute();
  let page;
  if (!section) page = <Home />;
  else if (section === 'exams') page = <Exams id={id} />;
  else if (section === 'questions') page = <Bank id={id} />;
  else if (section === 'interpretation') page = <Interpretation id={id} />;
  else if (section === 'coverage') page = <Coverage />;
  else page = <main className="page"><p>That page does not exist. <a href={href()}>Go to the start page</a></p></main>;

  return (
    <div className="app">
      <a className="skip" href="#content">Skip to content</a>
      <nav className="navbar" aria-label="Main navigation">
        <a className="logo" href={href()}>AnalyticsHub</a>
        <div className="nav-links">
          {NAV.map(([key, label]) => (
            <a key={key} href={href(key)} aria-current={section === key ? 'page' : undefined}>{label}</a>
          ))}
        </div>
      </nav>
      <div id="content">{page}</div>
      <footer>AnalyticsHub · Practice for the Data Analytics in Accounting oral exam.</footer>
    </div>
  );
}
