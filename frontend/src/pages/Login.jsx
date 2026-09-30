import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AlertCircle } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/chat';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password, rememberMe);
      navigate(from, { replace: true });
    } catch (err) {
      console.error('Login error:', err);
      if (err.code === 'ERR_NETWORK' || !err.response) {
        setError('Cannot connect to server (backend port 8000). Please ensure server is running.');
      } else {
        setError(err.response?.data?.detail || 'Invalid email or password.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
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
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="text-xs p-2.5 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] placeholder-[var(--subtle)] outline-none focus:border-[var(--accent)] transition-colors"
            />
          </div>

          <div className="flex items-center justify-between text-xs">
            <label className="flex items-center gap-2 cursor-pointer text-[var(--muted)]">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="accent-[var(--accent)]"
              />
              <span>Remember me</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-[6px] bg-[var(--accent)] text-white text-xs font-medium hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-40"
          >
            {loading ? 'Opening reading desk…' : 'Sign in'}
          </button>
        </form>

        {/* Demo Credentials */}
        <div className="pt-4 border-t border-[var(--line-subtle)] flex flex-col gap-2">
          <span className="text-[11px] font-mono text-[var(--muted)] text-center">
            Quick demo credentials:
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleDemoFill('student@example.com', 'student123')}
              className="py-1 px-2 rounded-[4px] border border-[var(--line)] bg-[var(--surface-muted)] hover:bg-[var(--surface-hover)] text-[11px] font-sans text-[var(--ink)] text-center transition-colors"
            >
              Demo Student
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('amit@university.edu', 'password123')}
              className="py-1 px-2 rounded-[4px] border border-[var(--line)] bg-[var(--surface-muted)] hover:bg-[var(--surface-hover)] text-[11px] font-sans text-[var(--ink)] text-center transition-colors"
            >
              Prof. Amit
            </button>
          </div>
        </div>

        <div className="text-center text-xs text-[var(--muted)]">
          Don't have an account?{' '}
          <Link to="/register" className="text-[var(--accent)] hover:underline font-medium">
            Create account
          </Link>
        </div>
      </div>
    </div>
  );
}
