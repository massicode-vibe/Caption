const API_BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export async function fetchStyles() {
  const res = await fetch(`${API_BASE}/api/styles`);
  return res.json();
}

export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function transcribeVideo({ taskId, groqApiKey, pacing = 'auto' }) {
  const res = await fetch(`${API_BASE}/api/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      groq_api_key: groqApiKey || undefined,
      pacing,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Transcription failed');
  }
  return res.json();
}

export async function renderVideo({
  taskId,
  phrases,
  words,
  styleId,
  positionPct,
  sizePct,
  accentColor,
}) {
  const res = await fetch(`${API_BASE}/api/render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      phrases,
      words,
      style_id: styleId,
      position_pct: positionPct,
      size_pct: sizePct,
      accent_color: accentColor,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Rendering failed');
  }
  return res.json();
}
