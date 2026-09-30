# StudyMate AI: UI/UX Design Guide
### Design direction: "a reading desk, not a chatbot"

Most AI projects look alike: purple-blue gradients, sparkle icons, robot avatars and floating chat bubbles. StudyMate AI should look like a **study tool**, closer to Notion, Readwise or a well-made ebook reader. Its main strength is citations, so the interface is built around the **source page** rather than the chat bubble.

---

## 1. Design Principles

1. **Evidence first.** Every answer sits next to the page it came from.
2. **Calm and readable.** Paper-like colours, book-like typography, no visual noise.
3. **Honest.** Show what the system is doing ("Reading page 12 of 45") and admit when nothing was found.
4. **Document-centred.** The user's PDFs are the hero, not the AI.
5. **Human voice.** Plain, friendly wording with no hype.

---

## 2. Visual Identity

### 2.1 Colour Palette

| Role | Colour | Hex |
|---|---|---|
| Background | Warm off-white | `#FAF8F4` |
| Surface / cards | White | `#FFFFFF` |
| Primary text | Ink near-black | `#1E1E24` |
| Muted text | Warm grey | `#6B6B70` |
| Borders | Hairline | `#E6E2DA` |
| Accent (buttons, active states) | Terracotta | `#C8553D` |
| Source highlight | Highlighter yellow | `#FFE9A8` |

**Dark mode ("night reading"):** background `#1B1A18`, text `#EDE8DF`, same terracotta accent slightly lightened. Avoid neon on black.

Use the accent sparingly: primary button and active states only.

### 2.2 Typography

| Use | Font | Why |
|---|---|---|
| Answers | Newsreader or Source Serif 4 | Reads like a textbook |
| Interface | IBM Plex Sans or Geist | Clean and neutral |
| File / page labels | JetBrains Mono | e.g. `DBMS_Unit3.pdf · p.14` |

### 2.3 Shape and Style
- 6 px corner radius, 1 px borders, almost no shadows.
- No gradients, glassmorphism or glowing effects.
- Line icons only (Lucide), thin and neutral.

---

## 3. What to Avoid

| Avoid | Why |
|---|---|
| Sparkle icons, "Ask AI anything" | Instantly reads as a generic AI product |
| Purple/blue gradients, glowing orbs | Overused AI look |
| Robot avatars, left/right chat bubbles | Feels like a messenger, not a study tool |
| Bouncing three-dot typing indicator | Gimmicky |
| Emoji in headings and buttons | Looks unprofessional |
| "How can I help you today?" | Generic, says nothing about your product |

---

## 4. Main Layout: Answer Beside Its Evidence

The chat screen uses a three-column reading layout.

```
┌───────────┬───────────────────────────────┬─────────────────────┐
│ Shelf     │ Question                      │ Source              │
│           │ What is normalization?        │ DBMS_Unit3.pdf · 14 │
│ [x] DBMS  │ ─────────────────────         │ ┌─────────────────┐ │
│ [x] ML    │ Normalization organizes       │ │ ...reduce       │ │
│ [ ] OS    │ tables to reduce redundancy   │ │ ▓▓redundancy▓▓  │ │
│           │ and improve integrity¹ ...    │ │ and improve...  │ │
│ Recent    │                               │ └─────────────────┘ │
│  ACID     │ ¹ DBMS_Unit3  p.14            │ [Open full page]    │
│  Joins    │ ² DBMS_Unit3  p.15            │                     │
│           │ ─────────────────────         │                     │
│           │ Ask a follow-up…              │                     │
└───────────┴───────────────────────────────┴─────────────────────┘
```

| Column | Content |
|---|---|
| **Left: the shelf** | PDFs with checkboxes to choose what to search; recent questions below |
| **Centre: the answer** | Each question is a heading; the answer is text beneath it, with no bubbles. Citations are small footnote-style superscripts |
| **Right: the source** | The real PDF page with the matching passage **highlighted in yellow** |

The highlighted source page is the signature feature. It makes answers verifiable at a glance.

**Mobile:** the three columns collapse into three tabs: Shelf · Answer · Source.

---

## 5. Key UX Ideas

| # | Idea | Description |
|---|---|---|
| 1 | Document-first onboarding | Empty state is a large drop zone: "Drop your notes here". No chat box until a document exists |
| 2 | Honest processing status | "Reading page 12 of 45…" then "Ready · 45 pages · 102 sections" instead of a spinner |
| 3 | Hover previews | Hovering a footnote shows a small tooltip of the source text |
| 4 | Calm streaming | Text appears steadily, with no blinking cursor or bouncing animation |
| 5 | Calm "not found" state | "Nothing in your selected notes covers this. Try selecting more documents." Styled as a normal message, not a red error |
| 6 | Suggested questions | After upload, show questions built from the document's headings, e.g. "What is a foreign key?" |
| 7 | Scope chips | Selected documents appear as chips above the input (`DBMS_Unit3 ×`), so the search scope is always clear |
| 8 | Keep / Save to notes | Pin a good answer with its citations to a Notes page; one-click export to Markdown or PDF |
| 9 | Keyboard shortcuts | `/` focus input · `Enter` send · `1`–`9` open citation · `Esc` close source panel |
| 10 | Retry and regenerate | Small text buttons under each answer, not large coloured ones |

---

## 6. Microcopy: Sound Like a Person

| Instead of | Write |
|---|---|
| "Ask AI anything" | "Ask your notes" |
| "AI is thinking…" | "Searching 3 documents…" |
| "Something went wrong" | "That upload didn't finish. Try again?" |
| "Generate" | "Find answer" |
| "Hallucination warning" | "Answers come only from your documents." |
| "No results" | "Nothing in your notes covers this yet." |
| "Upload file" | "Add to your shelf" |

---

## 7. Page-by-Page Design

### Login / Register
Centred card on the warm background, wordmark in serif, one line of text: "Ask your notes. Get answers with page numbers." No illustrations of robots or brains.

### Dashboard
- "Continue where you left off" card with the last question and document.
- Three plain numbers: documents, questions asked, pages indexed.
- Buttons: **Add document** (primary), **New question** (secondary).
- No decorative charts.

### Library
- Table columns: file name, pages, added date, status.
- Status shown as a small dot: grey (uploaded), amber (reading), green (ready), red (failed, with reason and Retry).
- Drag and drop works anywhere on the page.

### Chat (main screen)
The three-column layout from Section 4, plus scope chips, suggested questions and the input at the bottom.

### History
Grouped by date ("Today", "This week", "Earlier"), searchable, each entry showing the question and the first line of its answer. Rename, delete, export.

### Notes (Keep)
Saved answers displayed as cards with their footnotes, filterable by document. Export all as Markdown or PDF.

### Settings
Plain-language options instead of technical terms:

| Technical | Shown to the user as |
|---|---|
| `top_k` | "How many passages to search: Focused / Balanced / Broad" |
| `temperature` | Hidden (fixed low value) |
| LLM provider | "Answer engine: Cloud / On this computer" |
| Theme | Light / Night / Match system |

---

## 8. Component Guide

| Component | Style notes |
|---|---|
| Primary button | Terracotta fill, white text, 6 px radius, no shadow |
| Secondary button | 1 px border, transparent background |
| Input box | White surface, 1 px border, accent border on focus |
| Footnote marker | Small superscript number in accent colour, underline on hover |
| Source panel | White card, mono file label at top, highlighted passage in `#FFE9A8` |
| Scope chip | Rounded pill, muted background, small "×" |
| Status dot | 8 px circle, colour-coded, with text label beside it for accessibility |
| Toast | Small bottom-left message, auto-dismiss, no icons |
| Empty states | One plain sentence and one clear action |

---

## 9. Motion and Interaction

- Panel slide-in: about 150 ms ease-out.
- Hover previews: appear after 200 ms.
- No bounce, no parallax, no confetti.
- Respect `prefers-reduced-motion`.

---

## 10. Accessibility

- Text contrast at least WCAG AA (4.5:1) in both light and dark themes.
- Never rely on colour alone: status dots always have a text label.
- Full keyboard navigation with visible focus rings.
- Answer font size adjustable (small / medium / large).
- Screen-reader labels for citations ("Source 1: DBMS_Unit3, page 14").
- Responsive from 360 px wide phones upwards.

---

## 11. Implementation Notes

| Need | Suggested tool |
|---|---|
| Styling | Tailwind CSS with a custom theme using the palette above |
| Fonts | Google Fonts: Newsreader, IBM Plex Sans, JetBrains Mono |
| Icons | Lucide (line icons) |
| PDF viewer with highlights | `react-pdf` or PDF.js; draw yellow overlay rectangles from each chunk's stored text position |
| Animations | CSS transitions, or Framer Motion for panel slides only |
| Markdown in answers | `react-markdown` with a serif prose style |
| Theme switching | CSS variables on `:root`, toggled by a `data-theme` attribute |

### Tailwind theme sketch
```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      paper: "#FAF8F4",
      ink: "#1E1E24",
      muted: "#6B6B70",
      line: "#E6E2DA",
      accent: "#C8553D",
      mark: "#FFE9A8",
    },
    fontFamily: {
      serif: ["Newsreader", "Georgia", "serif"],
      sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
      mono: ["JetBrains Mono", "monospace"],
    },
    borderRadius: { DEFAULT: "6px" },
  },
}
```

### Data needed for the highlighted source view
Each chunk stored in the vector database should keep `document_id`, `page` and the text's bounding boxes on that page (from PyMuPDF `get_text("words")` or `search_for`). The frontend uses these to draw the yellow highlight.

---

## 12. UX Success Checklist

- [ ] A new user can upload a PDF and get a cited answer within 2 minutes.
- [ ] Every answer shows at least one clickable source with a highlighted passage.
- [ ] "Not found" is handled gracefully and is never blank or a raw error.
- [ ] No sparkle icons, gradients or robot imagery anywhere.
- [ ] Works on phone, tablet and desktop.
- [ ] Light and night themes both readable.
- [ ] Keyboard-only use is possible for the whole chat flow.
