import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { NotesProvider } from './context/NotesContext';
import { ToastProvider } from './context/ToastContext';
import ProtectedRoute from './components/layout/ProtectedRoute';
import AppShell from './components/layout/AppShell';

import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';
import Chat from './pages/Chat';
import Notes from './pages/Notes';
import History from './pages/History';
import Settings from './pages/Settings';

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <NotesProvider>
          <ToastProvider>
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
          </ToastProvider>
        </NotesProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
