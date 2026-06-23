import { useState, useEffect } from 'react';

const STORAGE_KEY = 'dpl_aisstream_api_key';

const STATUS_CONFIG = {
  disconnected: { label: 'Offline', color: '#7f8ea6', icon: 'cloud_off' },
  connecting:   { label: 'Connecting…', color: '#f7b23b', icon: 'sync' },
  connected:    { label: 'Live', color: '#2dd96f', icon: 'cell_tower' },
  error:        { label: 'Error', color: '#f44336', icon: 'error' },
};

/**
 * Overlay panel for the VesselTrafficMap that lets the user toggle live
 * AIS mode and enter their API key. The key is persisted in localStorage
 * so it survives page refreshes.
 */
export default function LiveAisPanel({ enabled, onToggle, status, vesselCount, apiKey, onApiKeyChange }) {
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [keyDraft, setKeyDraft] = useState('');
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.disconnected;

  // Hydrate from localStorage or Production Env Var on mount
  useEffect(() => {
    const prodKey = import.meta.env.VITE_AISSTREAM_API_KEY;
    const stored = localStorage.getItem(STORAGE_KEY);

    if (prodKey) {
      onApiKeyChange(prodKey);
      setKeyDraft(prodKey);
    } else if (stored) {
      onApiKeyChange(stored);
      setKeyDraft(stored);
    }
  }, [onApiKeyChange]);

  function handleSaveKey() {
    const trimmed = keyDraft.trim();
    if (trimmed) {
      localStorage.setItem(STORAGE_KEY, trimmed);
      onApiKeyChange(trimmed);
    }
    setShowKeyInput(false);
  }

  function handleClearKey() {
    localStorage.removeItem(STORAGE_KEY);
    onApiKeyChange(null);
    setKeyDraft('');
    setShowKeyInput(false);
  }

  return (
    <div className="absolute top-4 right-4 z-20 flex flex-col items-end gap-2">
      {/* ── Main toggle pill ──────────────────────────────────────────── */}
      <div className="bg-surface-container/90 backdrop-blur-sm border border-outline-variant rounded-lg shadow-[0px_4px_12px_rgba(0,0,0,0.5)] flex items-center gap-3 px-4 py-2">
        {/* Status dot */}
        <span
          className="inline-block w-2.5 h-2.5 rounded-full"
          style={{
            backgroundColor: cfg.color,
            boxShadow: status === 'connected' ? `0 0 8px ${cfg.color}` : 'none',
          }}
        />

        <span className="font-label-caps text-label-caps text-on-surface-variant select-none">
          {enabled ? cfg.label : 'Live AIS Off'}
        </span>

        {enabled && status === 'connected' && (
          <span className="font-data-mono text-data-mono text-on-surface text-xs">
            {vesselCount} vessel{vesselCount !== 1 ? 's' : ''}
          </span>
        )}

        {/* Toggle switch */}
        <button
          onClick={onToggle}
          className={`relative w-10 h-5 rounded-full transition-colors ${
            enabled ? 'bg-primary' : 'bg-surface-variant'
          }`}
          title={enabled ? 'Disable live AIS' : 'Enable live AIS'}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-on-primary transition-transform shadow-sm ${
              enabled ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>

        {/* Settings gear - Hidden if using a hardcoded prod key */}
        {!import.meta.env.VITE_AISSTREAM_API_KEY && (
          <button
            onClick={() => setShowKeyInput((s) => !s)}
            className="text-on-surface-variant hover:text-on-surface transition-colors"
            title="API Key settings"
          >
            <span className="material-symbols-outlined text-[18px]">settings</span>
          </button>
        )}
      </div>

      {/* ── API key input dropdown ────────────────────────────────────── */}
      {showKeyInput && (
        <div className="bg-surface-container/95 backdrop-blur-md border border-outline-variant rounded-lg shadow-[0px_4px_12px_rgba(0,0,0,0.5)] p-4 w-80">
          <label className="font-label-caps text-label-caps text-on-surface-variant block mb-2">
            AISStream API Key
          </label>
          <input
            type="password"
            value={keyDraft}
            onChange={(e) => setKeyDraft(e.target.value)}
            placeholder="Paste your API key here"
            className="w-full bg-surface border border-outline-variant rounded px-3 py-2 text-on-surface font-body-sm text-body-sm focus:outline-none focus:border-primary"
            onKeyDown={(e) => e.key === 'Enter' && handleSaveKey()}
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleSaveKey}
              className="flex-1 bg-primary text-on-primary py-1.5 rounded font-label-caps text-label-caps text-center hover:opacity-90 transition-opacity"
            >
              Save & Connect
            </button>
            {apiKey && (
              <button
                onClick={handleClearKey}
                className="px-3 py-1.5 border border-outline-variant text-on-surface-variant rounded font-label-caps text-label-caps hover:text-error hover:border-error transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant/60 mt-2">
            Key is stored in your browser only — never sent to our servers.
          </p>
        </div>
      )}
    </div>
  );
}
