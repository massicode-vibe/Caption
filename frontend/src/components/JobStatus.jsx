import React from 'react';

export function JobStatus({
  isRendering,
  renderProgress,
  renderResult,
  onReset
}) {
  if (isRendering) {
    return (
      <div className="result-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
          <span>Burning Captions with FFmpeg...</span>
          <span>{renderProgress || 'Working'}</span>
        </div>
        <div style={{ height: '4px', background: 'var(--surface-2)', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: '100%',
              background: 'var(--accent)',
              animation: 'shimmer 1.5s infinite linear',
            }}
          />
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-3)' }}>
          Rendering word-by-word animated ASS subtitles directly into your MP4...
        </p>
      </div>
    );
  }

  if (renderResult) {
    return (
      <div className="result-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '20px' }}>🎉</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '15px' }}>Video Ready for Export!</div>
            <div style={{ fontSize: '12px', color: 'var(--text-3)' }}>
              Animated word-timed captions successfully burned.
            </div>
          </div>
        </div>

        <div className="result-actions">
          <a
            className="btn btn-primary"
            href={renderResult.video_url}
            download={renderResult.mp4_filename}
          >
            ⬇️ Download MP4 Video
          </a>
          <a
            className="btn btn-secondary"
            href={renderResult.srt_url}
            download={renderResult.srt_filename}
          >
            📄 SRT Subtitles
          </a>
          <a
            className="btn btn-secondary"
            href={renderResult.ass_url}
            download={renderResult.ass_filename}
          >
            🎨 ASS File
          </a>
        </div>

        <div style={{ textAlign: 'center', marginTop: '6px' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ height: '34px', fontSize: '12px' }}
            onClick={onReset}
          >
            ↺ Caption Another Video
          </button>
        </div>
      </div>
    );
  }

  return null;
}
