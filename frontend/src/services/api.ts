import { Session, DatasetMetadata, Message } from '../types';

const API_BASE = '/api';

export async function fetchHealth(): Promise<{ status: string; groq_configured: boolean }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error('Failed to load sessions');
  return res.json();
}

export async function createSession(title?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title || 'New Analysis Session' }),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error('Failed to load session details');
  return res.json();
}

export async function updateSession(sessionId: string, title: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to update session');
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete session');
}

export async function uploadDataset(sessionId: string, file: File): Promise<DatasetMetadata> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/sessions/${sessionId}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload dataset');
  }
  return res.json();
}

export async function querySession(
  sessionId: string,
  prompt?: string,
  audioBlob?: Blob
): Promise<{ user_message: Message; assistant_message: Message; execution_time_ms?: number }> {
  const formData = new FormData();
  if (prompt) formData.append('prompt', prompt);
  if (audioBlob) formData.append('audio', audioBlob, 'voice_query.webm');

  const res = await fetch(`${API_BASE}/sessions/${sessionId}/query`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Query execution failed');
  }
  return res.json();
}

export async function createDemoDataset(): Promise<Session> {
  const res = await fetch(`${API_BASE}/create-demo-dataset`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to create demo dataset');
  return res.json();
}
