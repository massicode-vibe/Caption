import React, { useState } from 'react';

export function ReviewEditor({ phrases, onUpdatePhrases, onRevertOriginal }) {
  const [editingWordId, setEditingWordId] = useState(null);
  const [tempText, setTempText] = useState('');

  const totalWords = phrases.reduce((sum, p) => sum + (p.words?.length || 0), 0);

  const startEditing = (word) => {
    setEditingWordId(word.id);
    setTempText(word.text);
  };

  const saveWordText = (phraseIndex, wordIndex) => {
    if (!tempText.trim()) {
      setEditingWordId(null);
      return;
    }

    const updated = JSON.parse(JSON.stringify(phrases));
    updated[phraseIndex].words[wordIndex].text = tempText.trim();
    // Update phrase full text representation
    updated[phraseIndex].text = updated[phraseIndex].words.map((w) => w.text).join(' ');
    onUpdatePhrases(updated);
    setEditingWordId(null);
  };

  const toggleEmphasis = (phraseIndex, wordIndex, e) => {
    e.stopPropagation();
    const updated = JSON.parse(JSON.stringify(phrases));
    const curr = Boolean(updated[phraseIndex].words[wordIndex].emphasis);
    updated[phraseIndex].words[wordIndex].emphasis = !curr;
    onUpdatePhrases(updated);
  };

  return (
    <div className="review-box">
      <div className="review-header">
        <div>
          <span className="review-title">
            <span>✏️</span> Review & Correct Words
          </span>
          <p className="review-sub">
            Click any word to edit typos. Click the <em>italic</em> badge to toggle glowing serif style.
          </p>
        </div>
        <span
          style={{
            fontSize: '11px',
            background: 'var(--surface-2)',
            padding: '2px 8px',
            borderRadius: '6px',
            fontWeight: 600,
            border: '1px solid var(--border)',
          }}
        >
          {totalWords} words
        </span>
      </div>

      <div className="review-editor">
        {phrases.map((phrase, pIdx) => (
          <div key={phrase.id || pIdx} className="review-phrase">
            <div className="review-phrase-time">
              ⏱ {phrase.start.toFixed(2)}s → {phrase.end.toFixed(2)}s
            </div>

            <div className="review-phrase-words">
              {phrase.words.map((word, wIdx) => {
                const isEditing = (editingWordId === word.id);

                if (isEditing) {
                  return (
                    <input
                      key={word.id}
                      className="word-chip-input"
                      value={tempText}
                      autoFocus
                      onChange={(e) => setTempText(e.target.value)}
                      onBlur={() => saveWordText(pIdx, wIdx)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveWordText(pIdx, wIdx);
                        if (e.key === 'Escape') setEditingWordId(null);
                      }}
                    />
                  );
                }

                return (
                  <div
                    key={word.id}
                    className={`word-chip ${word.emphasis ? 'is-emphasis' : ''}`}
                    onClick={() => startEditing(word)}
                    title="Click to edit spelling"
                  >
                    <span>{word.text}</span>
                    <button
                      type="button"
                      style={{
                        fontSize: '11px',
                        opacity: word.emphasis ? 1 : 0.4,
                        padding: '0 2px',
                        fontStyle: 'italic',
                      }}
                      title="Toggle glowing italic serif emphasis"
                      onClick={(e) => toggleEmphasis(pIdx, wIdx, e)}
                    >
                      ✦
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {onRevertOriginal && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ height: '30px', fontSize: '11.5px', padding: '0 10px' }}
            onClick={onRevertOriginal}
          >
            ↺ Revert All Words
          </button>
        </div>
      )}
    </div>
  );
}
