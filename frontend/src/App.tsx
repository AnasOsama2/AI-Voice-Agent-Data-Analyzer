import React, { useState, useEffect, useRef } from 'react';
import { Session, DatasetMetadata } from './types';
import {
  fetchHealth,
  fetchSessions,
  createSession,
  fetchSession,
  deleteSession,
  uploadDataset,
  querySession,
  createDemoDataset,
} from './services/api';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { VoiceInputBar } from './components/VoiceInputBar';
import { DataSchemaModal } from './components/DataSchemaModal';
import { MessageSquare, Sparkles, AlertCircle, Bot, Loader2, Database } from 'lucide-react';

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [schemaModalOpen, setSchemaModalOpen] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize and check backend health
  useEffect(() => {
    checkHealthAndLoadSessions();
  }, []);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession?.messages, isLoading]);

  const checkHealthAndLoadSessions = async () => {
    try {
      const health = await fetchHealth();
      setIsBackendHealthy(health.status === 'healthy');
      const loadedSessions = await fetchSessions();
      setSessions(loadedSessions);

      if (loadedSessions.length > 0) {
        loadSessionDetails(loadedSessions[0].id);
      } else {
        handleCreateSession();
      }
    } catch (err) {
      console.error(err);
      setIsBackendHealthy(false);
    }
  };

  const loadSessionDetails = async (sessionId: string) => {
    try {
      setErrorMessage(null);
      const sessionData = await fetchSession(sessionId);
      setCurrentSession(sessionData);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load session');
    }
  };

  const handleCreateSession = async () => {
    try {
      setErrorMessage(null);
      const newSession = await createSession('New Analysis Session');
      setSessions((prev) => [newSession, ...prev]);
      setCurrentSession(newSession);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create new session');
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      const updated = sessions.filter((s) => s.id !== id);
      setSessions(updated);
      if (currentSession?.id === id) {
        if (updated.length > 0) {
          loadSessionDetails(updated[0].id);
        } else {
          handleCreateSession();
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete session');
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!currentSession) return;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      const metadata = await uploadDataset(currentSession.id, file);
      // Reload session
      await loadSessionDetails(currentSession.id);
      // Refresh sidebar sessions list
      const updatedSessions = await fetchSessions();
      setSessions(updatedSessions);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload dataset');
    } finally {
      setIsUploading(false);
    }
  };

  const handleLoadDemo = async () => {
    setIsUploading(true);
    setErrorMessage(null);
    try {
      const demoSession = await createDemoDataset();
      setSessions((prev) => [demoSession, ...prev.filter((s) => s.id !== demoSession.id)]);
      setCurrentSession(demoSession);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load demo dataset');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (prompt?: string, audioBlob?: Blob) => {
    if (!currentSession) return;
    setIsLoading(true);
    setErrorMessage(null);

    // Optimistic user message if text prompt
    if (prompt) {
      const tempUserMsg = {
        id: 'temp-' + Date.now(),
        session_id: currentSession.id,
        role: 'user' as const,
        content: prompt,
        created_at: new Date().toISOString(),
      };
      setCurrentSession((prev) =>
        prev
          ? {
              ...prev,
              messages: [...(prev.messages || []), tempUserMsg],
            }
          : null
      );
    }

    try {
      const result = await querySession(currentSession.id, prompt, audioBlob);
      // Update with server responses
      setCurrentSession((prev) => {
        if (!prev) return null;
        const filtered = (prev.messages || []).filter((m) => !m.id.startsWith('temp-'));
        return {
          ...prev,
          messages: [...filtered, result.user_message, result.assistant_message],
        };
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Error running analysis query');
      // Rollback optimistic message
      if (prompt) {
        setCurrentSession((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            messages: (prev.messages || []).filter((m) => !m.id.startsWith('temp-')),
          };
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const hasDataset = Boolean(currentSession?.file_name);
  const messages = currentSession?.messages || [];

  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <Header
        currentSession={currentSession}
        onOpenSchemaModal={() => setSchemaModalOpen(true)}
        onLoadDemo={handleLoadDemo}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main App Workspace */}
      <div className="app-main-layout">
        {/* Left Sidebar */}
        <Sidebar
          sessions={sessions}
          currentSessionId={currentSession?.id || null}
          onSelectSession={loadSessionDetails}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
          onFileUpload={handleFileUpload}
          onLoadDemo={handleLoadDemo}
          isUploading={isUploading}
        />

        {/* Central Chat & Analytics View */}
        <main className="chat-viewport">
          {/* Error Banner */}
          {errorMessage && (
            <div className="error-banner animate-fade-in">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-xs">{errorMessage}</span>
              <button className="btn btn-ghost btn-xs ml-auto" onClick={() => setErrorMessage(null)}>
                Dismiss
              </button>
            </div>
          )}

          {/* Messages Feed */}
          <div className="messages-scroll-area">
            {messages.length === 0 ? (
              <div className="welcome-hero animate-fade-in">
                <div className="hero-badge">
                  <Sparkles className="w-4 h-4 text-accent" />
                  <span>Next-Gen Voice & SQL Intelligence</span>
                </div>
                <h2 className="hero-title">Talk to Your Data</h2>
                <p className="hero-desc">
                  Upload a CSV or Excel spreadsheet, then speak or type your questions in{' '}
                  <strong>Arabic</strong> or <strong>English</strong>. The AI Agent will write safe
                  SQL, query the database, and generate dynamic visual charts.
                </p>

                {!hasDataset ? (
                  <div className="hero-action-card">
                    <p className="hero-action-title">Get Started by uploading data:</p>
                    <div className="flex gap-3 justify-center">
                      <button className="btn btn-primary" onClick={handleLoadDemo}>
                        <Sparkles className="w-4 h-4" />
                        <span>Try Sample Bilingual Sales Data</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="hero-action-card">
                    <p className="hero-action-title">
                      Dataset <code>{currentSession?.file_name}</code> loaded!
                    </p>
                    <p className="text-xs text-muted">
                      Click the microphone below to ask a question, or type in the input bar.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="messages-list">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}

                {isLoading && (
                  <div className="assistant-loading-indicator animate-fade-in">
                    <div className="message-avatar bot-avatar">
                      <Bot size={18} />
                    </div>
                    <div className="loading-bubble">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span className="text-xs text-muted font-medium">
                        Analyzing voice intent, running verified SQL & building charts...
                      </span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Bottom Voice & Text Input Bar */}
          <VoiceInputBar
            onSendMessage={handleSendMessage}
            isLoading={isLoading || isUploading}
            hasDataset={hasDataset}
          />
        </main>
      </div>

      {/* Dataset Schema & Sample Rows Modal */}
      <DataSchemaModal
        metadata={currentSession?.metadata || null}
        fileName={currentSession?.file_name}
        isOpen={schemaModalOpen}
        onClose={() => setSchemaModalOpen(false)}
      />
    </div>
  );
}
