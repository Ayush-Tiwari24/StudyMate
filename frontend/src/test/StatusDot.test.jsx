import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusDot from '../components/library/StatusDot';

describe('StatusDot component', () => {
  it('renders Uploaded status with grey dot and no pulse', () => {
    render(<StatusDot status="uploaded" />);
    expect(screen.getByText('Uploaded')).toBeInTheDocument();
    const dot = screen.getByTestId('status-dot');
    expect(dot).toHaveClass('bg-[var(--status-uploaded)]');
    expect(dot).not.toHaveClass('animate-pulse');
  });

  it('renders Reading status with orange dot and subtle pulse', () => {
    render(<StatusDot status="processing" />);
    expect(screen.getByText('Reading')).toBeInTheDocument();
    const dot = screen.getByTestId('status-dot');
    expect(dot).toHaveClass('bg-[var(--status-reading)]');
    expect(dot).toHaveClass('animate-pulse');
  });

  it('renders Ready status with green dot and no pulse', () => {
    render(<StatusDot status="ready" />);
    expect(screen.getByText('Ready')).toBeInTheDocument();
    const dot = screen.getByTestId('status-dot');
    expect(dot).toHaveClass('bg-[var(--status-ready)]');
    expect(dot).not.toHaveClass('animate-pulse');
  });

  it('renders Failed status with terracotta dot and no pulse', () => {
    render(<StatusDot status="failed" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
    const dot = screen.getByTestId('status-dot');
    expect(dot).toHaveClass('bg-[var(--status-failed)]');
    expect(dot).not.toHaveClass('animate-pulse');
  });

  it('allows custom label override', () => {
    render(<StatusDot status="ready" labelOverride="42 pages" />);
    expect(screen.getByText('42 pages')).toBeInTheDocument();
  });
});
