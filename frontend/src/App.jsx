import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Stage } from './components/Stage';
import { UploadPanel } from './components/UploadPanel';
import { StyleGrid } from './components/StyleGrid';
import { Controls } from './components/Controls';
import { ReviewEditor } from './components/ReviewEditor';
import { JobStatus } from './components/JobStatus';
import {
  fetchHealth,
  fetchStyles,
  uploadVideo,
  transcribeVideo,
  renderVideo
} from './utils/api';

export function App() {
  const [theme, setTheme] = useState(
    localStorage.getItem('cz_theme') || 'dark'
  );
  const [groqKey, setGroqKey] = useState(
    localStorage.getItem('groq_api_key') || ''
  );
  const [hasServerGroq, setHasServerGroq] = useState(false);

  // Studio config state
  const [styles, setStyles] = useState([]);
  const [selectedStyleId, setSelectedStyleId] = useState('style_11'); // Editorial Hybrid
  const [positionPct, setPositionPct] = useState(50);
  const [pacing, setPacing] = useState('auto');
  const [accentColor, setAccentColor] = useState('auto');
  const [sizePct, setSizePct] = useState(100);

  // Workflow state
  const [fileInfo, setFileInfo] = useState(null);
  const [phrases, setPhrases] = useState([]);
  const [originalPhrases, setOriginalPhrases] = useState([]);
  const [step, setStep] = useState('idle'); // 'idle', 'transcribed', 'rendered'
  const [isUploading, setIsUploading] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderResult, setRenderResult] = useState(null);
  const [error, setError] = useState(null);
  const [transcribeNote, setTranscribeNote] = useState('');

  // Apply theme attribute to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cz_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Initial load: styles and health
  useEffect(() => {
    fetchHealth()
      .then((data) => setHasServerGroq(Boolean(data.has_groq_env)))
      .catch(() => {});

    fetchStyles()
      .then((data) => {
        if (data.styles) {
          setStyles(data.styles);
        }
      })
      .catch((err) => console.error('Failed to load styles', err));
  }, []);

  const currentStyle = styles.find((s) => s.id === selectedStyleId) || {
    id: 'style_11',
    name: 'Editorial Hybrid',
    accent: '#FFFFFF',
    font_family_base: "'Inter', sans-serif",
    weight_base: '800',
  };

  // Upload handler
  const handleUpload = async (file) => {
    setError(null);
    setIsUploading(true);
    try {
      const data = await uploadVideo(file);
      setFileInfo(data);
      setRenderResult(null);
      setPhrases([]);
      setOriginalPhrases([]);
      setStep('uploaded');
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  // Transcribe handler
  const handleTranscribe = async () => {
    if (!fileInfo) return;
    setError(null);
    setIsTranscribing(true);
    setTranscribeNote('');
    try {
      const data = await transcribeVideo({
        taskId: fileInfo.task_id,
        groqApiKey: groqKey,
        pacing,
      });
      setPhrases(data.phrases || []);
      setOriginalPhrases(JSON.parse(JSON.stringify(data.phrases || [])));
      setTranscribeNote(data.note || '');
      setStep('transcribed');
    } catch (err) {
      setError(err.message || 'Transcription failed');
    } finally {
      setIsTranscribing(false);
    }
  };

  // Render handler
  const handleRender = async () => {
    if (!fileInfo || !phrases.length) return;
    setError(null);
    setIsRendering(true);
    try {
      const data = await renderVideo({
        taskId: fileInfo.task_id,
        phrases,
        styleId: selectedStyleId,
        positionPct,
        sizePct,
        accentColor,
      });
      setRenderResult(data);
      setStep('rendered');
    } catch (err) {
      setError(err.message || 'Rendering failed');
    } finally {
      setIsRendering(false);
    }
  };

  const handleClear = () => {
    setFileInfo(null);
    setPhrases([]);
    setOriginalPhrases([]);
    setRenderResult(null);
    setStep('idle');
    setError(null);
  };

  return (
    <div className="app-container">
      <Navbar
        theme={theme}
        toggleTheme={toggleTheme}
        groqKey={groqKey}
        setGroqKey={setGroqKey}
        hasServerGroq={hasServerGroq}
      />

      <main className="studio">
        {/* Left Column: Stage Preview */}
        <section className="stage-col" aria-label="Preview">
          <Stage
            videoUrl={fileInfo?.video_url}
            phrases={phrases}
            currentStyle={currentStyle}
            positionPct={positionPct}
            onPositionChange={setPositionPct}
            sizePct={sizePct}
            accentColor={accentColor}
            resultVideoUrl={renderResult?.video_url}
          />

          <div style={{ textAlign: 'center', maxWidth: '420px', marginTop: '4px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: '700' }}>
              {currentStyle.name}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-3)', marginTop: '2px' }}>
              {renderResult
                ? 'Rendered video with burned word-by-word captions.'
                : fileInfo
                ? 'Drag slider or click & drag on video to reposition.'
                : 'Upload a clip to preview word-by-word captions.'}
            </p>
          </div>
        </section>

        {/* Right Column: Controls & Configuration */}
        <section className="panel" aria-label="Caption Settings">
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '700', letterSpacing: '-0.02em' }}>
              Caption a Video
            </h1>
            <p style={{ color: 'var(--text-2)', fontSize: '13px', marginTop: '4px' }}>
              Auto-transcribe with word timestamps, customize typography, and export.
            </p>
          </div>

          {error && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'var(--danger-soft)',
                color: 'var(--danger)',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>⚠️ {error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                style={{ fontWeight: 600, textDecoration: 'underline' }}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Upload Panel */}
          <UploadPanel
            fileInfo={fileInfo}
            onUpload={handleUpload}
            onClear={handleClear}
            isLoading={isUploading}
          />

          {/* Caption Styles Selector */}
          <StyleGrid
            styles={styles}
            selectedStyleId={selectedStyleId}
            onSelectStyle={setSelectedStyleId}
          />

          {/* Position, Size, Color Controls */}
          <Controls
            positionPct={positionPct}
            onPositionChange={setPositionPct}
            pacing={pacing}
            onPacingChange={setPacing}
            accentColor={accentColor}
            onAccentChange={setAccentColor}
            sizePct={sizePct}
            onSizeChange={setSizePct}
            currentStyle={currentStyle}
          />

          {/* Action Area */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '6px' }}>
            {step === 'uploaded' && (
              <div>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={isTranscribing}
                  onClick={handleTranscribe}
                >
                  {isTranscribing ? '⏳ Transcribing Speech...' : '⚡ Transcribe & Generate Captions'}
                </button>
                <p style={{ fontSize: '12px', color: 'var(--text-3)', textAlign: 'center', marginTop: '6px' }}>
                  Uses Groq Whisper API for word-level timestamps.
                </p>
              </div>
            )}

            {/* Review & Typo Editor */}
            {phrases.length > 0 && !renderResult && (
              <>
                {transcribeNote && (
                  <div style={{ fontSize: '12px', color: 'var(--text-3)', padding: '6px 10px', background: 'var(--surface-2)', borderRadius: '6px' }}>
                    ℹ️ {transcribeNote}
                  </div>
                )}

                <ReviewEditor
                  phrases={phrases}
                  onUpdatePhrases={setPhrases}
                  onRevertOriginal={() => setPhrases(JSON.parse(JSON.stringify(originalPhrases)))}
                />

                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={isRendering}
                  onClick={handleRender}
                >
                  {isRendering ? '🎬 Rendering Video...' : '✨ Confirm & Render Video'}
                </button>
              </>
            )}

            {/* Render Job Progress & Results */}
            <JobStatus
              isRendering={isRendering}
              renderResult={renderResult}
              onReset={handleClear}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
