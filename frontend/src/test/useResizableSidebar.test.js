import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useResizableSidebar } from '../hooks/useResizableSidebar';

describe('useResizableSidebar hook', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with default width when localStorage is empty', () => {
    const { result } = renderHook(() =>
      useResizableSidebar({
        initialWidth: 288,
        minWidth: 200,
        maxWidth: 500,
        storageKey: 'test_sidebar_width',
      })
    );

    expect(result.current.width).toBe(288);
    expect(result.current.isDragging).toBe(false);
  });

  it('restores stored width from localStorage', () => {
    localStorage.setItem('test_sidebar_width', '350');

    const { result } = renderHook(() =>
      useResizableSidebar({
        initialWidth: 288,
        minWidth: 200,
        maxWidth: 500,
        storageKey: 'test_sidebar_width',
      })
    );

    expect(result.current.width).toBe(350);
  });

  it('clamps width within min and max constraints on drag', () => {
    const { result } = renderHook(() =>
      useResizableSidebar({
        initialWidth: 288,
        minWidth: 200,
        maxWidth: 500,
        direction: 'left',
      })
    );

    // Simulate drag start at x = 100
    act(() => {
      result.current.startResize({
        type: 'mousedown',
        button: 0,
        clientX: 100,
        preventDefault: () => {},
      });
    });

    expect(result.current.isDragging).toBe(true);

    // Drag past max (move to x = 800) -> delta = +700 -> 288 + 700 = 988 -> clamped to 500
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 800 }));
    });

    expect(result.current.width).toBe(500);

    // Drag below min (move to x = -200) -> delta = -300 -> clamped to 200
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: -200 }));
    });

    expect(result.current.width).toBe(200);

    // Mouse up ends drag
    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });

    expect(result.current.isDragging).toBe(false);
  });

  it('resets width to default with resetWidth', () => {
    localStorage.setItem('test_sidebar_width', '450');

    const { result } = renderHook(() =>
      useResizableSidebar({
        initialWidth: 288,
        minWidth: 200,
        maxWidth: 500,
        storageKey: 'test_sidebar_width',
      })
    );

    expect(result.current.width).toBe(450);

    act(() => {
      result.current.resetWidth();
    });

    expect(result.current.width).toBe(288);
    expect(localStorage.getItem('test_sidebar_width')).toBe('288');
  });

  it('handles right sidebar drag correctly (dragging left increases width)', () => {
    const { result } = renderHook(() =>
      useResizableSidebar({
        initialWidth: 384,
        minWidth: 280,
        maxWidth: 700,
        direction: 'right',
        storageKey: 'test_right_width',
      })
    );

    expect(result.current.width).toBe(384);

    // Mouse down at x = 900
    act(() => {
      result.current.startResize({
        type: 'mousedown',
        button: 0,
        clientX: 900,
        preventDefault: () => {},
      });
    });

    // Drag left by 100px (to x = 800) -> for right sidebar, delta is startX - currentX = 900 - 800 = +100
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 800 }));
    });

    expect(result.current.width).toBe(484);

    // Drag right by 150px (to x = 1050) -> delta = 900 - 1050 = -150 -> 384 - 150 = 234 -> clamped to min 280
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 1050 }));
    });

    expect(result.current.width).toBe(280);

    // Release mouse
    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });

    expect(result.current.isDragging).toBe(false);
    expect(localStorage.getItem('test_right_width')).toBe('280');
  });

  it('supports dynamic maxWidth function', () => {
    let dynamicMax = 420;
    const { result } = renderHook(() =>
      useResizableSidebar({
        initialWidth: 300,
        minWidth: 200,
        maxWidth: () => dynamicMax,
        direction: 'left',
      })
    );

    act(() => {
      result.current.startResize({
        type: 'mousedown',
        button: 0,
        clientX: 100,
        preventDefault: () => {},
      });
    });

    // Drag to 600
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 700 }));
    });

    // Clamped by dynamicMax (420)
    expect(result.current.width).toBe(420);

    // DynamicMax updates
    dynamicMax = 350;
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 700 }));
    });

    expect(result.current.width).toBe(350);

    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });
  });
});
