import React from 'react';

export function Controls({
  positionPct,
  onPositionChange,
  pacing,
  onPacingChange,
  accentColor,
  onAccentChange,
  sizePct,
  onSizeChange,
  currentStyle
}) {
  const PRESET_COLORS = [
    { label: 'White', value: '#FFFFFF' },
    { label: 'Yellow', value: '#FFE600' },
    { label: 'Cyan', value: '#00E5FF' },
    { label: 'Red', value: '#FF4154' },
    { label: 'Green', value: '#22C55E' },
  ];

  return (
    <>
      {/* Position Control */}
      <div className="group">
        <div className="group-label">
          <span>Vertical Position</span>
          <span className="range-val">{positionPct}%</span>
        </div>
        <div className="range-row">
          <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>Top</span>
          <input
            type="range"
            min="10"
            max="88"
            step="1"
            value={positionPct}
            onChange={(e) => onPositionChange(Number(e.target.value))}
          />
          <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>Bottom</span>
        </div>
        <div className="seg" style={{ marginTop: '4px' }}>
          <button
            type="button"
            className={positionPct === 18 ? 'is-active' : ''}
            onClick={() => onPositionChange(18)}
          >
            Top (18%)
          </button>
          <button
            type="button"
            className={positionPct === 50 ? 'is-active' : ''}
            onClick={() => onPositionChange(50)}
          >
            Middle (50%)
          </button>
          <button
            type="button"
            className={positionPct === 82 ? 'is-active' : ''}
            onClick={() => onPositionChange(82)}
          >
            Bottom (82%)
          </button>
        </div>
      </div>

      {/* Words on Screen */}
      <div className="group">
        <div className="group-label">
          <span>Words on Screen</span>
          <span>Pacing</span>
        </div>
        <div className="seg">
          <button
            type="button"
            className={pacing === 'auto' ? 'is-active' : ''}
            onClick={() => onPacingChange('auto')}
          >
            Auto
          </button>
          <button
            type="button"
            className={pacing === '1' ? 'is-active' : ''}
            onClick={() => onPacingChange('1')}
          >
            One
          </button>
          <button
            type="button"
            className={pacing === '2-3' ? 'is-active' : ''}
            onClick={() => onPacingChange('2-3')}
          >
            Short (2-3)
          </button>
          <button
            type="button"
            className={pacing === 'sentence' ? 'is-active' : ''}
            onClick={() => onPacingChange('sentence')}
          >
            Clause
          </button>
        </div>
      </div>

      {/* Highlight Color */}
      <div className="group">
        <div className="group-label">
          <span>Highlight Color</span>
          <span>Accent</span>
        </div>
        <div className="swatches">
          <button
            type="button"
            className={`swatch swatch-auto ${accentColor === 'auto' ? 'is-active' : ''}`}
            onClick={() => onAccentChange('auto')}
          >
            <span
              className="dot"
              style={{ background: currentStyle?.accent || '#FFFFFF' }}
            ></span>
            Default
          </button>

          {PRESET_COLORS.map((c) => (
            <button
              key={c.value}
              type="button"
              className={`swatch ${accentColor === c.value ? 'is-active' : ''}`}
              style={{ background: c.value }}
              title={c.label}
              onClick={() => onAccentChange(c.value)}
            />
          ))}

          <label className="swatch swatch-custom" title="Custom color picker">
            <input
              type="color"
              value={accentColor === 'auto' ? '#E07A55' : accentColor}
              onChange={(e) => onAccentChange(e.target.value)}
            />
          </label>
        </div>
      </div>

      {/* Text Size */}
      <div className="group">
        <div className="group-label">
          <span>Text Size</span>
          <span className="range-val">{sizePct}%</span>
        </div>
        <div className="range-row">
          <input
            type="range"
            min="50"
            max="180"
            step="5"
            value={sizePct}
            onChange={(e) => onSizeChange(Number(e.target.value))}
          />
        </div>
      </div>
    </>
  );
}
