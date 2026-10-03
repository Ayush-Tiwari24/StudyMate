import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);

// Development performance logging (LCP and initial JS size)
if (import.meta.env.DEV && typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    setTimeout(() => {
      try {
        const perfEntries = performance.getEntriesByType('resource');
        const jsEntries = perfEntries.filter((e) => e.initiatorType === 'script' || e.name.endsWith('.js'));
        const totalJsBytes = jsEntries.reduce((acc, e) => acc + (e.transferSize || e.encodedBodySize || 0), 0);
        console.info(`[Perf] Initial JS Transfer Size: ${(totalJsBytes / 1024).toFixed(1)} KB across ${jsEntries.length} files`);

        const paintEntries = performance.getEntriesByType('paint');
        for (const p of paintEntries) {
          console.info(`[Perf] Paint (${p.name}): ${p.startTime.toFixed(1)} ms`);
        }
      } catch (err) {
        console.debug('[Perf] Performance metrics unavailable:', err);
      }
    }, 1000);
  });
}
