import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SourcePanel from '../components/source/SourcePanel';

describe('SourcePanel component', () => {
  const mockSources = [
    {
      id: 1,
      document_id: 10,
      file: 'algorithms_notes.pdf',
      page: 24,
      snippet: 'Asymptotic notation describes algorithm running time bounds.',
    },
    {
      id: 2,
      document_id: 10,
      file: 'algorithms_notes.pdf',
      page: 37,
      snippet: 'Recurrence relations define running times recursively.',
    },
  ];

  it('renders placeholder when sources array is empty', () => {
    render(
      <SourcePanel
        isOpen={true}
        sources={[]}
      />
    );

    expect(
      screen.getByText(/Select any footnote citation \(such as ¹ or ²\) in the answer to inspect its original page\./i)
    ).toBeInTheDocument();
  });

  it('renders citation details, tabs, and cited passage when sources are provided', () => {
    const handleSelectCitation = vi.fn();
    render(
      <SourcePanel
        isOpen={true}
        sources={mockSources}
        activeCitationIndex={1}
        onSelectCitation={handleSelectCitation}
      />
    );

    // Document name and page in header
    expect(screen.getByText(/algorithms_notes\.pdf · p\.24/i)).toBeInTheDocument();

    // Citation switcher tabs
    expect(screen.getByRole('tab', { name: /\[1\] p\.24/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /\[2\] p\.37/i })).toBeInTheDocument();

    // Cited passage snippet
    expect(screen.getByText(/Asymptotic notation describes algorithm running time bounds\./i)).toBeInTheDocument();

    // Clicking second tab switches citation
    fireEvent.click(screen.getByRole('tab', { name: /\[2\] p\.37/i }));
    expect(handleSelectCitation).toHaveBeenCalledWith(mockSources[1], 2);
  });
});
