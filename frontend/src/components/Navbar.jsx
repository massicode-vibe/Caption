import React, { useState } from 'react';

export function Navbar({ theme, toggleTheme, groqKey, setGroqKey, hasServerGroq }) {
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [inputKey, setInputKey] = useState(groqKey || '');

  const saveKey = () => {
    setGroqKey(inputKey.trim());
    localStorage.setItem('groq_api_key', inputKey.trim());
    setShowKeyModal(false);
  };

  const isConfigured = Boolean(groqKey || hasServerGroq);

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true"></span>
            <span>Captionizer Studio</span>
          </div>

          <div className="topbar-right">
            <button
              className="btn-api-key"
              onClick={() => setShowKeyModal(true)}
              title="Configure Groq Whisper API Key for free real-time transcription"
            >
              <span className={`badge-active ${isConfigured ? '' : 'style-inactive'}`} style={{ background: isConfigured ? 'var(--success)' : '#eab308' }}></span>
              <span>{isConfigured ? 'Groq API Active' : 'Enter Groq Key'}</span>
            </button>

            <button
              className="btn-api-key"
              onClick={toggleTheme}
              title="Toggle dark / light theme"
            >
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>
          </div>
        </div>
      </header>

      {showKeyModal && (
        <div className="modal-overlay" onClick={() => setShowKeyModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Groq Whisper API Key</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-3)' }}>
              Groq provides free, ultra-fast Whisper speech-to-text with word-level timestamps.
              Get your free key from <a href="https://console.groq.com/" target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', textDecoration: 'underline' }}>console.groq.com</a>.
            </p>
            <input
              type="password"
              placeholder="gsk_..."
              value={inputKey}
              onChange={(e) => setInputKey(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border-strong)',
                background: 'var(--surface-2)',
                color: 'var(--text)',
                outline: 'none',
                fontFamily: 'monospace'
              }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button
                className="btn btn-secondary"
                style={{ height: '36px', padding: '0 14px' }}
                onClick={() => setShowKeyModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ height: '36px', padding: '0 16px', width: 'auto' }}
                onClick={saveKey}
              >
                Save Key
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
