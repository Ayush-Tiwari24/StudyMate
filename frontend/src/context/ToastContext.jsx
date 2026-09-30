import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext({
  toast: () => {},
});

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const toast = useCallback((message, durationMs = 3500) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, durationMs);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast Container: bottom-left, small, no icons */}
      <div
        className="fixed bottom-4 left-4 z-50 flex flex-col gap-2 pointer-events-none max-w-sm"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] rounded-[6px] px-3.5 py-2 text-xs font-sans shadow-sm"
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
