import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { NotesProvider } from './context/NotesContext';
import { ToastProvider } from './context/ToastContext';
import ProtectedRoute from './components/layout/ProtectedRoute';
import AppShell from './components/layout/AppShell';

function lazyWithRetry(importFn) {
  return React.lazy(async () => {
    try {
      return await importFn();
    } catch (err) {
      const reloadKey = 'studymate_chunk_reload';
      if (!sessionStorage.getItem(reloadKey)) {
        sessionStorage.setItem(reloadKey, '1');
        window.location.reload();
        return;
      }
      throw err;
    }
  });
}

const Login = lazyWithRetry(() => import('./pages/Login'));
const Register = lazyWithRetry(() => import('./pages/Register'));
const Dashboard = lazyWithRetry(() => import('./pages/Dashboard'));
const Library = lazyWithRetry(() => import('./pages/Library'));
const Chat = lazyWithRetry(() => import('./pages/Chat'));
const Notes = lazyWithRetry(() => import('./pages/Notes'));
const History = lazyWithRetry(() => import('./pages/History'));
const Settings = lazyWithRetry(() => import('./pages/Settings'));

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error, info) {
    console.error('StudyMate ErrorBoundary caught:', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--paper)] p-4 select-none">
          <div className="w-full max-w-sm bg-[var(--surface)] border border-[var(--line)] rounded-[6px] shadow-sm p-6 flex flex-col items-center gap-4 text-center">
            <h2 className="font-serif text-xl font-medium text-[var(--ink)]">Something went wrong</h2>
            <p className="text-xs text-[var(--muted)]">StudyMate encountered an error while loading. Please refresh to try again.</p>
            <button
              type="button"
              onClick={() => {
                sessionStorage.clear();
                window.location.href = '/login';
              }}
              className="px-4 py-2 bg-[var(--accent)] text-white text-xs font-medium rounded-[6px] hover:bg-[var(--accent-hover)] transition-colors"
            >
              Refresh &amp; Return to Login
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function PageLoader() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-50 dark:bg-slate-900 transition-colors">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Loading StudyMate...</span>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <NotesProvider>
            <ToastProvider>
              <React.Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Navigate to="/chat" replace />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <Chat />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/chat/:chatId"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <Chat />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <Dashboard />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/library"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <Library />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/notes"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <Notes />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/history"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <History />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <AppShell>
                      <Settings />
                    </AppShell>
                  </ProtectedRoute>
                }
              />

              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          </React.Suspense>
        </ToastProvider>
        </NotesProvider>
      </AuthProvider>
    </ThemeProvider>
  </ErrorBoundary>
  );
}
