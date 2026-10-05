import React, { useRef, useState } from 'react';

export function UploadPanel({ fileInfo, onUpload, onClear, isLoading }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onUpload(files[0]);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files[0]);
    }
  };

  return (
    <div className="group">
      <div className="group-label">
        <span>Video Source</span>
        {fileInfo && <span>{fileInfo.duration?.toFixed(1)}s</span>}
      </div>

      {!fileInfo ? (
        <div
          className={`drop ${isDragOver ? 'is-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div style={{ fontSize: '28px', color: 'var(--accent)' }}>🎬</div>
          <strong>{isLoading ? 'Processing Video...' : 'Drop a video here or browse'}</strong>
          <small>MP4, MOV, WEBM or MKV (up to 2GB)</small>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept="video/*,.mp4,.mov,.webm,.mkv"
            onChange={handleFileChange}
          />
        </div>
      ) : (
        <div className="file-row">
          <div style={{ fontSize: '22px', color: 'var(--accent)' }}>🎞️</div>
          <div className="file-meta">
            <div className="file-name">{fileInfo.filename}</div>
            <div className="file-sub">
              {fileInfo.width}×{fileInfo.height} • {fileInfo.duration?.toFixed(1)} seconds
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ height: '32px', padding: '0 10px', fontSize: '12px' }}
            onClick={onClear}
          >
            Change
          </button>
        </div>
      )}
    </div>
  );
}
