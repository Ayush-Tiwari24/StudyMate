import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AnswerBlock from '../components/chat/AnswerBlock';

describe('AnswerBlock component', () => {
  it('renders question and clean markdown answer with no footnote numbers', () => {
    render(
      <AnswerBlock
        question="How does divide and conquer work?"
        answer="Divide and conquer splits the problem into subproblems. Then it merges solutions."
      />
    );

    expect(screen.getByText('How does divide and conquer work?')).toBeInTheDocument();
    expect(
      screen.getByText('Divide and conquer splits the problem into subproblems. Then it merges solutions.')
    ).toBeInTheDocument();

    // Verify no footnote markers or footnotes list
    expect(screen.queryByLabelText('Footnotes')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Source/i })).not.toBeInTheDocument();
  });

  it('renders NotFoundNotice when answer indicates absence in documents', () => {
    render(
      <AnswerBlock
        question="What is quantum gravity?"
        answer="Nothing in your selected notes covers this. Try selecting more documents."
      />
    );

    expect(
      screen.getByText(/Nothing in your selected notes covers this/i)
    ).toBeInTheDocument();
  });

  it('renders markdown tables cleanly without citation artifacts', () => {
    render(
      <AnswerBlock
        question="Definitions table"
        answer={`| Concept | Complexity |
|---|---|
| Recurrence | O(log n) |`}
      />
    );

    expect(screen.getByText('Recurrence')).toBeInTheDocument();
    expect(screen.getByText('O(log n)')).toBeInTheDocument();
    expect(screen.queryByLabelText('Footnotes')).not.toBeInTheDocument();
  });
});
