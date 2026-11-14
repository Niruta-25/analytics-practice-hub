import { useState } from 'react';

// Hint-based help for one question. The student must show an attempt first, and
// the tutor replies with the next step, not the solution. The request goes to
// our own /api/help endpoint, which holds the API key on the server.
export default function AiHelp({ questionId, placeholder }) {
  const [attempt, setAttempt] = useState('');
  const [problem, setProblem] = useState('');
  const [reply, setReply] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/help', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ questionId, attempt, problem }),
      });
      const isJson = (response.headers.get('content-type') || '').includes('application/json');
      if (!isJson) throw new Error('AI help is only available on the hosted site.');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Something went wrong. Try again.');
      setReply(data);
    } catch (problemFound) {
      setError(problemFound instanceof TypeError ? 'The AI help could not be reached. Check your connection and try again.' : problemFound.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <details className="ai-help">
      <summary>Get a hint from AI</summary>
      <p className="muted">Show what you have tried. You get the next step, not the answer.</p>
      <label>
        What I have so far
        <textarea rows="4" maxLength="3000" value={attempt} onChange={(e) => setAttempt(e.target.value)} placeholder={placeholder} />
      </label>
      <label>
        What happens, or where I am stuck (optional)
        <textarea rows="2" maxLength="1500" value={problem} onChange={(e) => setProblem(e.target.value)} placeholder="An error message, a wrong result, or the step you cannot see" />
      </label>
      <button className="btn btn-primary" onClick={ask} disabled={busy || !attempt.trim()}>
        {busy ? 'Thinking…' : reply ? 'Ask again' : 'Ask AI'}
      </button>
      <div role="status">
        {error && <p className="ai-error">{error}</p>}
        {reply && !error && (
          <div className="ai-reply">
            <h3>Hint</h3>
            <p>{reply.reply}</p>
            {reply.cutOff && <p className="muted">This reply was cut short. Ask again for the rest.</p>}
          </div>
        )}
      </div>
    </details>
  );
}
