import React from 'react';

/**
 * HighlightOverlay renders yellow highlight rectangles over the PDF page.
 * bboxes are normalised coordinates { x0, y0, x1, y1 } between 0 and 1.
 */
export default function HighlightOverlay({ bboxes = [], pageWidth = 0, pageHeight = 0 }) {
  if (!bboxes || bboxes.length === 0 || !pageWidth || !pageHeight) {
    return null;
  }

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{ width: `${pageWidth}px`, height: `${pageHeight}px` }}
      aria-hidden="true"
    >
      {bboxes.map((box, i) => {
        const left = box.x0 * pageWidth;
        const top = box.y0 * pageHeight;
        const width = (box.x1 - box.x0) * pageWidth;
        const height = (box.y1 - box.y0) * pageHeight;

        return (
          <div
            key={i}
            className="absolute rounded-[2px]"
            style={{
              left: `${left}px`,
              top: `${top}px`,
              width: `${Math.max(width, 10)}px`,
              height: `${Math.max(height, 14)}px`,
              backgroundColor: 'var(--mark)',
              mixBlendMode: 'multiply',
              opacity: 0.7,
            }}
          />
        );
      })}
    </div>
  );
}
