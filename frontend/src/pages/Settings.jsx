import React, { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api/settings';
import { deleteAccount } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';
import { Check, AlertCircle, Trash2 } from 'lucide-react';

export default function Settings() {
  const { theme, setTheme, fontScale, setFontScale } = useTheme();
  const { logout } = useAuth();
  const { toast } = useToast();

  const [settings, setSettingsState] = useState({
    theme: theme,
    llm_provider: 'groq',
    model_name: 'openai/gpt-oss-120b',
    top_k: 5,
    font_scale: fontScale || 'medium',
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await getSettings();
        if (res.data && Object.keys(res.data).length > 0) {
          setSettingsState((prev) => ({
            ...prev,
            ...res.data,
            theme: localStorage.getItem('studymate_theme') || res.data.theme || 'light',
          }));
        }
      } catch (err) {
        console.error('Failed to load settings:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSavedSuccess(false);

    try {
      await updateSettings({
        theme: settings.theme,
        llm_provider: settings.llm_provider,
        model_name: settings.model_name,
        top_k: settings.top_k,
      });

      // Apply theme & font scale
      setTheme(settings.theme);
      if (setFontScale) {
        setFontScale(settings.font_scale);
      }

      setSavedSuccess(true);
      toast('Preferences saved');
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
      setError('Could not update preferences. Try again.');
      toast('Could not update preferences.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--paper)] p-6 md:p-10">
      <div className="max-w-2xl mx-auto flex flex-col gap-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[var(--ink)] tracking-tight">
              Preferences
            </h1>
            <p className="text-xs md:text-sm text-[var(--muted)] font-sans mt-1">
              Configure reading display, search scope, and citation preferences.
            </p>
          </div>

          {savedSuccess && (
            <div className="inline-flex items-center gap-1.5 text-xs text-[var(--status-ready)] font-mono">
              <Check size={14} />
              <span>Saved</span>
            </div>
          )}
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-[var(--muted)]">
            Loading preferences…
          </div>
        ) : (
          <form onSubmit={handleSave} className="flex flex-col gap-6">
            {error && (
              <div className="p-3 rounded-[6px] bg-[var(--accent-subtle)] text-[var(--status-failed)] text-xs flex items-center gap-2">
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}

            {/* Display & Reading Theme */}
            <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-5 flex flex-col gap-4 shadow-xs">
              <h2 className="font-serif text-base font-semibold text-[var(--ink)]">
                Reading Display
              </h2>

              <div className="flex flex-col gap-3">
                <label className="text-xs font-medium text-[var(--muted)] font-sans">
                  Reading Theme
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setSettingsState((p) => ({ ...p, theme: 'light' }));
                      setTheme('light');
                    }}
                    className={`p-3 rounded-[6px] border text-left flex flex-col gap-1 transition-colors ${
                      settings.theme === 'light'
                        ? 'border-[var(--accent)] bg-[var(--paper)]'
                        : 'border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--surface-hover)]'
                    }`}
                  >
                    <span className="text-xs font-medium text-[var(--ink)]">
                      Paper Reading
                    </span>
                    <span className="text-[11px] text-[var(--muted)]">
                      Warm off-white #FAF8F4, ink text
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setSettingsState((p) => ({ ...p, theme: 'night' }));
                      setTheme('night');
                    }}
                    className={`p-3 rounded-[6px] border text-left flex flex-col gap-1 transition-colors ${
                      settings.theme === 'night'
                        ? 'border-[var(--accent)] bg-[#242320]'
                        : 'border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--surface-hover)]'
                    }`}
                  >
                    <span className="text-xs font-medium text-[var(--ink)]">
                      Night Reading
                    </span>
                    <span className="text-[11px] text-[var(--muted)]">
                      Calm dark slate #1B1A18, warm ink
                    </span>
                  </button>
                </div>
              </div>

              {/* Text Size Scale */}
              <div className="flex flex-col gap-2 pt-3 border-t border-[var(--line-subtle)]">
                <label className="text-xs font-medium text-[var(--muted)] font-sans">
                  Answer Text Size
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: 'small', label: 'Compact (15px)' },
                    { key: 'medium', label: 'Standard (17px)' },
                    { key: 'large', label: 'Spacious (19px)' },
                  ].map((size) => (
                    <button
                      key={size.key}
                      type="button"
                      onClick={() => {
                        setSettingsState((p) => ({ ...p, font_scale: size.key }));
                        if (setFontScale) setFontScale(size.key);
                      }}
                      className={`py-2 px-3 rounded-[6px] border text-xs font-sans transition-colors ${
                        settings.font_scale === size.key
                          ? 'border-[var(--accent)] bg-[var(--surface-muted)] text-[var(--ink)] font-medium'
                          : 'border-[var(--line)] bg-[var(--surface)] text-[var(--muted)] hover:bg-[var(--surface-hover)]'
                      }`}
                    >
                      {size.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Retrieval Engine */}
            <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-5 flex flex-col gap-4 shadow-xs">
              <h2 className="font-serif text-base font-semibold text-[var(--ink)]">
                Retrieval Engine
              </h2>

              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-medium text-[var(--ink)] block">
                      Citation Evidence Depth (Top-K)
                    </label>
                    <span className="text-[11px] text-[var(--muted)]">
                      Number of candidate passages inspected per question.
                    </span>
                  </div>
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--line)] text-[var(--ink)]">
                    {settings.top_k} passages
                  </span>
                </div>

                <input
                  type="range"
                  min="2"
                  max="10"
                  step="1"
                  value={settings.top_k}
                  onChange={(e) =>
                    setSettingsState((p) => ({ ...p, top_k: parseInt(e.target.value, 10) }))
                  }
                  className="w-full accent-[var(--accent)] cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-[var(--line-subtle)]">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--muted)]">
                    LLM Provider
                  </label>
                  <select
                    value={settings.llm_provider}
                    onChange={(e) => {
                      const val = e.target.value;
                      let defaultModel = settings.model_name;
                      if (val === 'groq') defaultModel = 'openai/gpt-oss-120b';
                      else if (val === 'openai') defaultModel = 'gpt-4o-mini';
                      else if (val === 'ollama') defaultModel = 'llama3.2:3b';
                      setSettingsState((p) => ({
                        ...p,
                        llm_provider: val,
                        model_name: defaultModel,
                      }));
                    }}
                    className="text-xs p-2 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] outline-none focus:border-[var(--accent)]"
                  >
                    <option value="groq">Groq (Blazing Fast LPU)</option>
                    <option value="openai">OpenAI</option>
                    <option value="ollama">Ollama (Local / Free)</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--muted)]">
                    Model
                  </label>
                  <input
                    type="text"
                    value={settings.model_name}
                    onChange={(e) =>
                      setSettingsState((p) => ({ ...p, model_name: e.target.value }))
                    }
                    className="text-xs p-2 rounded-[6px] border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] outline-none focus:border-[var(--accent)] font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 rounded-[6px] bg-[var(--accent)] text-white text-xs font-medium hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-40"
              >
                {saving ? 'Saving…' : 'Save preferences'}
              </button>
            </div>
          </form>
        )}

        {/* Danger Zone: Account Deletion */}
        {!loading && (
          <div className="bg-[var(--surface)] border border-rose-200 dark:border-rose-900/40 rounded-xl p-6 flex flex-col gap-4 shadow-xs">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-sans text-sm font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                  <Trash2 size={14} />
                  <span>Danger Zone: Delete Account</span>
                </h2>
                <p className="text-xs text-[var(--muted)] font-sans mt-1 leading-relaxed">
                  Permanently erase your account, all uploaded PDF materials, vector embeddings, chats, and saved notes. This action is irreversible.
                </p>
              </div>

              <button
                type="button"
                onClick={async () => {
                  if (
                    window.confirm(
                      'Are you absolutely sure you want to permanently delete your account? All your uploaded notes, chats, and vector embeddings will be wiped immediately.'
                    )
                  ) {
                    setDeletingAccount(true);
                    try {
                      await deleteAccount();
                      toast('Account permanently deleted.');
                      logout();
                    } catch (err) {
                      console.error('Account deletion failed:', err);
                      toast('Failed to delete account. Please try again.');
                      setDeletingAccount(false);
                    }
                  }
                }}
                disabled={deletingAccount}
                className="px-3.5 py-1.5 rounded-[6px] bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium transition-colors disabled:opacity-50 flex-shrink-0"
              >
                {deletingAccount ? 'Deleting…' : 'Delete Account'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
