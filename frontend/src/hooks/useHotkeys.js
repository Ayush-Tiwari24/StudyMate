import { useEffect } from 'react';

/**
 * useHotkeys hook to bind key combinations cleanly
 * @param {Object} keyMap - e.g. { '/': () => focusInput(), 'Escape': () => closePanel() }
 * @param {Array} deps - dependencies array
 */
export function useHotkeys(keyMap = {}, deps = []) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Don't intercept typing in inputs or textareas for normal keys unless specifically handled
      const isInput =
        event.target.tagName === 'INPUT' ||
        event.target.tagName === 'TEXTAREA' ||
        event.target.isContentEditable;

      const key = event.key;

      if (key === '/' && !isInput && keyMap['/']) {
        event.preventDefault();
        keyMap['/'](event);
        return;
      }

      if (key === 'Escape' && keyMap['Escape']) {
        event.preventDefault();
        keyMap['Escape'](event);
        return;
      }

      if (key === '?' && !isInput && keyMap['?']) {
        event.preventDefault();
        keyMap['?'](event);
        return;
      }

      // Check numeric keys 1-9 for citation opening when not typing
      if (!isInput && /^[1-9]$/.test(key) && keyMap[key]) {
        event.preventDefault();
        keyMap[key](Number(key), event);
        return;
      }

      // Exact match handler
      if (keyMap[key] && (!isInput || key === 'Escape')) {
        keyMap[key](event);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, deps);
}
