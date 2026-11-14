import { useState } from 'react';
import { RATINGS, recordAttempt } from '../lib/progress.js';

// Shown once the answer is revealed: the student compares their own result with
// the checked answer and says how it went. This is what feeds the skill coverage map.
export default function SelfRating({ questionId, skill }) {
  const [chosen, setChosen] = useState('');
  const rate = (rating) => {
    if (chosen) return;
    recordAttempt(questionId, skill, rating);
    setChosen(rating);
  };
  return (
    <div className="rating">
      <span className="rating-label">Compare with your own result. How did it go?</span>
      <div className="rating-buttons">
        {RATINGS.map(([value, label]) => (
          <button
            key={value}
            className={`btn rating-${value} ${chosen === value ? 'chosen' : ''}`}
            onClick={() => rate(value)}
            disabled={Boolean(chosen) && chosen !== value}
            aria-pressed={chosen === value}
          >
            {label}
          </button>
        ))}
      </div>
      <span role="status" className="muted">{chosen ? 'Saved to your skill coverage.' : ''}</span>
    </div>
  );
}
