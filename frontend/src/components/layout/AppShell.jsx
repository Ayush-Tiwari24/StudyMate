import React from 'react';
import Navbar from './Navbar';

export default function AppShell({ children }) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[var(--paper)]">
      <Navbar />
      <div className="flex-1 overflow-hidden flex">{children}</div>
    </div>
  );
}
