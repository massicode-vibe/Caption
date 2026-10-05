import React, { useRef, useState, useEffect } from 'react';

export function Stage({
  videoUrl,
  phrases,
  currentStyle,
  positionPct,
  onPositionChange,
  sizePct,
  accentColor,
  resultVideoUrl
}) {
  const videoRef = useRef(null);
  const stageRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // Toggle Play / Pause
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  // Drag-to-reposition logic
  const handleMouseDown = (e) => {
    setIsDragging(true);
    updatePositionFromEvent(e);
  };

  const updatePositionFromEvent = (e) => {
    if (!stageRef.current) return;
    const rect = stageRef.current.getBoundingClientRect();
    const clientY = e.clientY ?? (e.touches ? e.touches[0].clientY : 0);
    const relativeY = clientY - rect.top;
    const pct = Math.round((relativeY / rect.height) * 100);
    const clamped = Math.max(12, Math.min(88, pct));
    onPositionChange(clamped);
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) updatePositionFromEvent(e);
    };
    const handleMouseUp = () => {
      if (isDragging) setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      window.addEventListener('touchmove', handleMouseMove);
      window.addEventListener('touchend', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleMouseMove);
      window.removeEventListener('touchend', handleMouseUp);
    };
  }, [isDragging]);

  // Find active phrase and active word based on currentTime
  let activePhrase = null;
  let activeWordId = null;

  if (phrases && phrases.length > 0) {
    for (const phrase of phrases) {
      if (currentTime >= phrase.start && currentTime <= phrase.end) {
        activePhrase = phrase;
        break;
      }
    }
    // If not strictly within start/end, find closest
    if (!activePhrase) {
      for (let i = 0; i < phrases.length; i++) {
        if (currentTime < phrases[i].start) {
          activePhrase = (i > 0) ? phrases[i - 1] : phrases[0];
          break;
        }
      }
      if (!activePhrase && phrases.length > 0) {
        activePhrase = phrases[phrases.length - 1];
      }
    }

    if (activePhrase && activePhrase.words) {
      for (const w of activePhrase.words) {
        if (currentTime >= w.start && currentTime <= w.end) {
          activeWordId = w.id;
          break;
        }
      }
    }
  }

  // Determine effective highlight color
  const effectiveAccent = (accentColor === 'auto')
    ? (currentStyle?.accent || '#FFFFFF')
    : accentColor;

  // Base font size scaling relative to preview container
  const baseScale = (sizePct / 100.0);
  const normalFontSize = `${Math.round(26 * baseScale)}px`;
  const emphasisFontSize = `${Math.round(34 * baseScale)}px`;

  return (
    <div className="stage-wrap">
      <div className="stage" ref={stageRef} id="stage">
        <span className="stage-tag">
          {resultVideoUrl ? 'Rendered Result' : 'Live Preview'}
        </span>

        {/* Video Player */}
        <video
          ref={videoRef}
          src={resultVideoUrl || videoUrl || undefined}
          playsInline
          loop
          onClick={togglePlay}
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />

        {/* Play/Pause Button Overlay */}
        {!isPlaying && (
          <button
            type="button"
            className="stage-play-btn"
            onClick={togglePlay}
            aria-label="Play video"
          >
            ▶
          </button>
        )}

        {/* Live Word-by-Word Caption Overlay */}
        {!resultVideoUrl && activePhrase && (
          <div
            className="caption-layer"
            style={{
              top: `${positionPct}%`,
            }}
          >
            {activePhrase.words.map((word) => {
              const isActive = (word.id === activeWordId);
              const isEmphasis = Boolean(word.emphasis);

              if (currentStyle.id === 'style_11') {
                // EDITORIAL HYBRID (From user image!)
                if (isEmphasis) {
                  return (
                    <span
                      key={word.id}
                      style={{
                        fontFamily: "'Instrument Serif', Georgia, serif",
                        fontStyle: 'italic',
                        fontWeight: 400,
                        fontSize: emphasisFontSize,
                        color: isActive ? effectiveAccent : '#FFFFFF',
                        opacity: isActive ? 1 : 0.65,
                        textShadow: isActive
                          ? '0 0 10px rgba(255,255,255,0.95), 0 0 22px rgba(255,255,255,0.6)'
                          : '0 1px 4px rgba(0,0,0,0.6)',
                        transition: 'all 0.08s ease-out',
                        transform: isActive ? 'scale(1.05)' : 'scale(1)',
                        display: 'inline-block',
                      }}
                    >
                      {word.text}
                    </span>
                  );
                }

                return (
                  <span
                    key={word.id}
                    style={{
                      fontFamily: "'Inter', 'SF Pro Display', sans-serif",
                      fontWeight: 800,
                      fontSize: normalFontSize,
                      color: isActive ? effectiveAccent : '#FFFFFF',
                      opacity: isActive ? 1 : 0.45,
                      transform: `scaleY(1.08) ${isActive ? 'scale(1.03)' : 'scale(1)'}`,
                      textShadow: '0 2px 8px rgba(0,0,0,0.7), 0 1px 2px rgba(0,0,0,0.5)',
                      transition: 'all 0.08s ease-out',
                      display: 'inline-block',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {word.text}
                  </span>
                );
              }

              // Other Styles Fallback / Rendering
              const isHighlightWord = isActive || isEmphasis;
              return (
                <span
                  key={word.id}
                  style={{
                    fontFamily: currentStyle.font_family_base,
                    fontWeight: currentStyle.weight_base,
                    fontSize: normalFontSize,
                    color: isHighlightWord ? effectiveAccent : '#FFFFFF',
                    opacity: isActive ? 1 : 0.5,
                    textShadow: currentStyle.shadow_base,
                    transform: isActive ? 'scale(1.05)' : 'scale(1)',
                    display: 'inline-block',
                    transition: 'all 0.08s ease-out',
                  }}
                >
                  {word.text}
                </span>
              );
            })}
          </div>
        )}

        {/* Drag overlay to adjust caption position */}
        {!resultVideoUrl && (
          <div
            className={`stage-drag-overlay ${isDragging ? 'is-dragging' : ''}`}
            onMouseDown={handleMouseDown}
            onTouchStart={handleMouseDown}
            title="Click and drag up or down to set caption position"
          >
            <div
              className="stage-drag-indicator"
              style={{ top: `${positionPct}%`, opacity: isDragging ? 0.95 : undefined }}
            >
              <div className="stage-drag-pill">
                ↕ {positionPct}%
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
