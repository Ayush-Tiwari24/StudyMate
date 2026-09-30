import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { submitFeedback } from '../api/chat';

export default function FeedbackButtons({ messageId }) {
  const [feedback, setFeedback] = useState(null); // 1, -1, or null
  const [submitting, setSubmitting] = useState(false);

  if (!messageId) return null;

  const handleFeedback = async (val) => {
    if (submitting) return;
    const newVal = feedback === val ? null : val;
    setSubmitting(true);
    try {
      if (newVal !== null) {
        await submitFeedback(messageId, newVal);
        setFeedback(newVal);
      } else {
        setFeedback(null);
      }
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="feedback-buttons-group">
      <button
        type="button"
        onClick={() => handleFeedback(1)}
        disabled={submitting}
        className={`feedback-btn ${feedback === 1 ? 'active-thumbs-up' : ''}`}
        title="Helpful answer"
        aria-label="Thumbs up"
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        onClick={() => handleFeedback(-1)}
        disabled={submitting}
        className={`feedback-btn ${feedback === -1 ? 'active-thumbs-down' : ''}`}
        title="Unhelpful or inaccurate answer"
        aria-label="Thumbs down"
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </button>

      {feedback !== null && (
        <span className="feedback-thankyou-label">
          <Check className="w-3 h-3 text-emerald-400 inline" /> Recorded
        </span>
      )}
    </div>
  );
}
