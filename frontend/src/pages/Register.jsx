import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AlertCircle } from 'lucide-react';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);

    try {
      await register(name, email, password);
      navigate('/chat', { replace: true });
    } catch (err) {
      console.error('Registration error:', err);
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--paper)] p-4 select-none">
      <div className="w-full max-w-sm bg-[var(--surface)] border border-[var(--line)] rounded-[6px] shadow-sm p-8 flex flex-col gap-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="font-serif text-3xl font-medium text-[var(--ink)] tracking-tight">
            StudyMate AI
          </h1>
          <p className="text-xs text-[var(--muted)] font-sans mt-1.5">
            Ask your notes. Get answers with page numbers.
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-2.5 rounded-[4px] bg-[var(--accent-subtle)] text-[var(--status-failed)] text-xs border border-[var(--line)]">
            <AlertCircle size={14} className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted)]">Full Name</label>
            <input
              type="text"
              required
              placeholder="Amit Sharma"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-xs p-2.5 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] placeholder-[var(--subtle)] outline-none focus:border-[var(--accent)] transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted)]">Email address</label>
            <input
              type="email"
              required
              placeholder="student@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="text-xs p-2.5 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] placeholder-[var(--subtle)] outline-none focus:border-[var(--accent)] transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted)]">Password</label>
            <input
              type="password"
              required
              placeholder="At least 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="text-xs p-2.5 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] placeholder-[var(--subtle)] outline-none focus:border-[var(--accent)] transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted)]">Confirm Password</label>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="text-xs p-2.5 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] placeholder-[var(--subtle)] outline-none focus:border-[var(--accent)] transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-[6px] bg-[var(--accent)] text-white text-xs font-medium hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-40 mt-1"
          >
            {loading ? 'Creating your shelf…' : 'Create account'}
          </button>
        </form>

        <div className="text-center text-xs text-[var(--muted)]">
          Already have an account?{' '}
          <Link to="/login" className="text-[var(--accent)] hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
