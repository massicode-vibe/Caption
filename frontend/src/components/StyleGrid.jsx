import React from 'react';

export function StyleGrid({ styles, selectedStyleId, onSelectStyle }) {
  return (
    <div className="group">
      <div className="group-label">
        <span>Caption Style</span>
        <span>{styles.length} styles</span>
      </div>

      <div className="styles">
        {styles.map((s) => {
          const isSelected = (s.id === selectedStyleId);
          return (
            <div
              key={s.id}
              className={`tile ${isSelected ? 'is-active' : ''}`}
              onClick={() => onSelectStyle(s.id)}
            >
              <div className="tile-thumb">
                <div dangerouslySetInnerHTML={{ __html: s.sample_html }} />
              </div>
              <div className="tile-name">
                <span>{s.name}</span>
                {isSelected && <span style={{ color: 'var(--accent)', fontSize: '14px' }}>✓</span>}
              </div>
              <div className="tile-desc">{s.tagline}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
