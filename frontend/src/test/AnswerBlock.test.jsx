import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AnswerBlock from '../components/chat/AnswerBlock';

describe('AnswerBlock component', () => {
  const mockSources = [
    {
      id: 'src-1',
      file: 'algorithms_lecture.pdf',
      page: 14,
      snippet: 'Divide and conquer breaks down problems recursively.',
    },
    {
      id: 'src-2',
      file: 'data_structures.pdf',
      page: 88,
      snippet: 'Binary search tree lookup takes O(h) time.',
    },
  ];

  it('renders question and formatted answer with footnote markers for [1]', () => {
    const handleSelectCitation = vi.fn();
    render(
      <AnswerBlock
        question="How does divide and conquer work?"
        answer="Divide and conquer splits the problem into subproblems [1]. Then it merges solutions [2]."
        sources={mockSources}
        onSelectCitation={handleSelectCitation}
      />
    );

    expect(screen.getByText('How does divide and conquer work?')).toBeInTheDocument();

    // Check footnote markers rendered as superscripts
    const cite1 = screen.getByRole('button', { name: /Source 1/i });
    expect(cite1).toBeInTheDocument();
    expect(cite1).toHaveTextContent('¹');

    const cite2 = screen.getByRole('button', { name: /Source 2/i });
    expect(cite2).toBeInTheDocument();
    expect(cite2).toHaveTextContent('²');

    // Click footnote marker triggers onSelectCitation
    fireEvent.click(cite1);
    expect(handleSelectCitation).toHaveBeenCalledWith(mockSources[0], 1);
  });

  it('renders NotFoundNotice when answer indicates absence in documents', () => {
    render(
      <AnswerBlock
        question="What is quantum gravity?"
        answer="Nothing in your selected notes covers this. Try selecting more documents."
        sources={[]}
      />
    );

    expect(
      screen.getByText(/Nothing in your selected notes covers this/i)
    ).toBeInTheDocument();
  });

  it('renders FootnoteList below answer with file and page numbers', () => {
    render(
      <AnswerBlock
        question="What is BST time complexity?"
        answer="It takes O(h) time [2]."
        sources={mockSources}
      />
    );

    expect(screen.getByLabelText('Footnotes')).toBeInTheDocument();
    expect(screen.getByText(/algorithms_lecture\.pdf/)).toBeInTheDocument();
    expect(screen.getByText(/· p\.14/)).toBeInTheDocument();
    expect(screen.getByText(/data_structures\.pdf/)).toBeInTheDocument();
    expect(screen.getByText(/· p\.88/)).toBeInTheDocument();
  });

  it('handles multiple grouped citations like [1, 2] in tables', () => {
    const handleSelectCitation = vi.fn();
    render(
      <AnswerBlock
        question="Definitions table"
        answer="| Concept | Source |\n|---|---|\n| Recurrence | [1, 2] |"
        sources={mockSources}
        onSelectCitation={handleSelectCitation}
      />
    );

    const cite1 = screen.getByRole('button', { name: /Source 1/i });
    const cite2 = screen.getByRole('button', { name: /Source 2/i });
    expect(cite1).toBeInTheDocument();
    expect(cite2).toBeInTheDocument();

    fireEvent.click(cite2);
    expect(handleSelectCitation).toHaveBeenCalledWith(mockSources[1], 2);
  });
});
