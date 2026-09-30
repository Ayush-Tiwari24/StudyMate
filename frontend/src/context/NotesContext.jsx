import { createContext, useContext, useState, useEffect } from 'react';

const NotesContext = createContext({
  savedNotes: [],
  saveNote: () => {},
  removeNote: () => {},
  isNoteSaved: () => false,
});

export function NotesProvider({ children }) {
  const [savedNotes, setSavedNotes] = useState(() => {
    try {
      const stored = localStorage.getItem('studymate_saved_notes');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('studymate_saved_notes', JSON.stringify(savedNotes));
    } catch (e) {
      console.error('Failed to persist notes:', e);
    }
  }, [savedNotes]);

  const saveNote = (note) => {
    // Note object: { id, question, answer, sources, savedAt }
    setSavedNotes((prev) => {
      if (prev.some((n) => n.id === note.id || (n.question === note.question && n.answer === note.answer))) {
        return prev;
      }
      return [{ ...note, id: note.id || Date.now(), savedAt: new Date().toISOString() }, ...prev];
    });
  };

  const removeNote = (noteId) => {
    setSavedNotes((prev) => prev.filter((n) => n.id !== noteId));
  };

  const isNoteSaved = (question, answer) => {
    return savedNotes.some((n) => n.question === question && n.answer === answer);
  };

  return (
    <NotesContext.Provider value={{ savedNotes, saveNote, removeNote, isNoteSaved }}>
      {children}
    </NotesContext.Provider>
  );
}

export function useNotes() {
  return useContext(NotesContext);
}
