import { useEffect, useRef, useState } from 'react';

function clock(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// Countdown for a timed exam. Elapsed time is measured from the wall clock, so
// the timer stays correct when the browser tab is in the background.
export default function Timer({ minutes, note }) {
  const total = minutes * 60;
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const startedAt = useRef(0);
  const carried = useRef(0);

  useEffect(() => {
    if (!running) return undefined;
    startedAt.current = Date.now();
    const tick = setInterval(() => {
      setElapsed(carried.current + (Date.now() - startedAt.current) / 1000);
    }, 250);
    return () => {
      clearInterval(tick);
      carried.current += (Date.now() - startedAt.current) / 1000;
    };
  }, [running]);

  const reset = () => {
    setRunning(false);
    carried.current = 0;
    setElapsed(0);
  };

  const remaining = total - elapsed;
  const over = remaining <= 0;
  const state = over ? 'over' : remaining <= 60 ? 'low' : 'ok';

  return (
    <section className={`timer timer-${state}`} aria-label="Exam timer">
      <div className="timer-clocks">
        <div>
          <span className="label">Time remaining</span>
          <strong role="timer">{clock(remaining)}</strong>
        </div>
        <div>
          <span className="label">Elapsed</span>
          <strong role="timer">{clock(elapsed)}</strong>
        </div>
      </div>
      <p className="timer-note">{note}</p>
      <div className="timer-buttons">
        <button className="btn btn-primary" onClick={() => setRunning(true)} disabled={running}>
          {elapsed > 0 ? 'Resume' : 'Start timer'}
        </button>
        <button className="btn" onClick={() => setRunning(false)} disabled={!running}>
          Pause
        </button>
        <button className="btn" onClick={reset} disabled={elapsed === 0}>
          Reset
        </button>
      </div>
      <p className="timer-status" role="status">
        {over ? 'Time is up. In the exam you would stop here; keep going to finish the practice.' : ''}
      </p>
    </section>
  );
}
