import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Hook for managing resizable sidebar widths with drag handles,
 * constraint clamping, localStorage persistence, and double-click reset.
 *
 * @param {Object} options
 * @param {number} options.initialWidth - Default width in pixels
 * @param {number} [options.minWidth=200] - Minimum width constraint
 * @param {number|(() => number)} [options.maxWidth=600] - Maximum width constraint (or dynamic accessor)
 * @param {string} [options.storageKey] - Key for localStorage persistence
 * @param {'left'|'right'} [options.direction='left'] - 'left' for left sidebar, 'right' for right sidebar
 */
export function useResizableSidebar({
  initialWidth,
  minWidth = 200,
  maxWidth = 600,
  storageKey,
  direction = 'left',
}) {
  const getComputedMax = useCallback(() => {
    return typeof maxWidth === 'function' ? maxWidth() : maxWidth;
  }, [maxWidth]);

  const [width, setWidth] = useState(() => {
    const computedMax = typeof maxWidth === 'function' ? maxWidth() : maxWidth;
    if (storageKey && typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = parseInt(saved, 10);
          if (!isNaN(parsed) && parsed >= minWidth && parsed <= computedMax) {
            return parsed;
          }
        }
      } catch {
        // Ignore localStorage access errors
      }
    }
    return initialWidth;
  });

  const [isDragging, setIsDragging] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(width);
  const overlayRef = useRef(null);

  // Clean up any lingering overlay or body styling on unmount
  useEffect(() => {
    return () => {
      if (typeof document !== 'undefined') {
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
        if (overlayRef.current) {
          overlayRef.current.remove();
          overlayRef.current = null;
        }
      }
    };
  }, []);

  const startResize = useCallback(
    (e) => {
      if (e.type === 'mousedown' && e.button !== 0) return;
      e.preventDefault();

      const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
      startXRef.current = clientX;
      startWidthRef.current = width;
      setIsDragging(true);

      if (typeof document !== 'undefined') {
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'col-resize';

        // Transparent overlay prevents any iframe or embedded elements from swallowing mouse events
        if (!overlayRef.current) {
          const overlay = document.createElement('div');
          overlay.id = 'resize-drag-overlay';
          overlay.style.position = 'fixed';
          overlay.style.inset = '0';
          overlay.style.zIndex = '99999';
          overlay.style.cursor = 'col-resize';
          overlay.style.userSelect = 'none';
          document.body.appendChild(overlay);
          overlayRef.current = overlay;
        }
      }

      const handleMove = (moveEvent) => {
        const currentX = moveEvent.type.startsWith('touch')
          ? moveEvent.touches[0].clientX
          : moveEvent.clientX;

        const delta = direction === 'left' ? currentX - startXRef.current : startXRef.current - currentX;
        const currentMax = getComputedMax();
        const newWidth = Math.max(minWidth, Math.min(startWidthRef.current + delta, currentMax));
        setWidth(newWidth);
      };

      const handleEnd = () => {
        setIsDragging(false);
        if (typeof document !== 'undefined') {
          document.body.style.userSelect = '';
          document.body.style.cursor = '';
          if (overlayRef.current) {
            overlayRef.current.remove();
            overlayRef.current = null;
          }
        }
        window.removeEventListener('mousemove', handleMove);
        window.removeEventListener('mouseup', handleEnd);
        window.removeEventListener('touchmove', handleMove);
        window.removeEventListener('touchend', handleEnd);

        setWidth((finalWidth) => {
          if (storageKey && typeof window !== 'undefined') {
            try {
              localStorage.setItem(storageKey, String(finalWidth));
            } catch {
              // Ignore localStorage errors
            }
          }
          return finalWidth;
        });
      };

      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleEnd);
      window.addEventListener('touchmove', handleMove);
      window.addEventListener('touchend', handleEnd);
    },
    [width, minWidth, getComputedMax, direction, storageKey]
  );

  const resetWidth = useCallback(() => {
    setWidth(initialWidth);
    if (storageKey && typeof window !== 'undefined') {
      try {
        localStorage.setItem(storageKey, String(initialWidth));
      } catch {
        // Ignore localStorage errors
      }
    }
  }, [initialWidth, storageKey]);

  return {
    width,
    setWidth,
    isDragging,
    startResize,
    resetWidth,
  };
}
