import React, { useState } from 'react';
import { Mic, MicOff, Send, Square, Sparkles, Globe } from 'lucide-react';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';

interface VoiceInputBarProps {
  onSendMessage: (prompt?: string, audioBlob?: Blob) => void;
  isLoading: boolean;
  hasDataset: boolean;
}

export const VoiceInputBar: React.FC<VoiceInputBarProps> = ({
  onSendMessage,
  isLoading,
  hasDataset,
}) => {
  const [textPrompt, setTextPrompt] = useState('');
  const {
    isRecording,
    recordingTime,
    startRecording,
    stopRecording,
    resetRecording,
    error: micError,
  } = useVoiceRecorder();

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textPrompt.trim() || isLoading) return;
    onSendMessage(textPrompt.trim());
    setTextPrompt('');
  };

  const handleToggleVoice = async () => {
    if (isRecording) {
      const blob = await stopRecording();
      if (blob) {
        onSendMessage(undefined, blob);
      }
    } else {
      await startRecording();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const sampleQuestions = [
    { en: 'Show top 5 sales by region', ar: 'أعلى 5 مبيعات حسب المنطقة' },
    { en: 'Average revenue per product category', ar: 'متوسط الإيراد لكل فئة منتجات' },
    { en: 'Total units sold vs unit price correlation', ar: 'إجمالي الوحدات المباعة مقابل السعر' },
  ];

  return (
    <div className="voice-input-container">
      {/* Quick Prompts Chips */}
      {hasDataset && !isRecording && (
        <div className="quick-prompts-bar">
          <span className="quick-prompts-label">
            <Sparkles className="w-3 h-3 text-accent" /> Suggested:
          </span>
          {sampleQuestions.map((q, idx) => (
            <button
              key={idx}
              className="quick-chip"
              onClick={() => onSendMessage(q.en)}
              disabled={isLoading}
            >
              <span>{q.en}</span>
              <span className="chip-arabic">{q.ar}</span>
            </button>
          ))}
        </div>
      )}

      {/* Recording Waveform Banner */}
      {isRecording && (
        <div className="recording-banner animate-pulse-subtle">
          <div className="recording-indicator">
            <span className="recording-dot"></span>
            <span className="recording-time font-mono">{formatTime(recordingTime)}</span>
          </div>
          <div className="waveform-animation">
            <span className="wave-bar bar-1"></span>
            <span className="wave-bar bar-2"></span>
            <span className="wave-bar bar-3"></span>
            <span className="wave-bar bar-4"></span>
            <span className="wave-bar bar-5"></span>
            <span className="wave-bar bar-6"></span>
            <span className="wave-bar bar-7"></span>
            <span className="wave-bar bar-8"></span>
          </div>
          <div className="recording-lang-hint">
            <Globe className="w-3.5 h-3.5" />
            <span>Speaking Arabic or English...</span>
          </div>
          <button className="btn btn-danger btn-sm" onClick={resetRecording} title="Cancel recording">
            Cancel
          </button>
        </div>
      )}

      {micError && <div className="mic-error-banner text-xs text-danger">{micError}</div>}

      <form className="input-bar-form" onSubmit={handleSendText}>
        <button
          type="button"
          className={`mic-button ${isRecording ? 'recording' : ''}`}
          onClick={handleToggleVoice}
          disabled={isLoading || !hasDataset}
          title={isRecording ? 'Stop and send voice recording' : 'Speak your question in Arabic or English'}
        >
          {isRecording ? <Square className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        <input
          type="text"
          className="text-query-input"
          placeholder={
            !hasDataset
              ? 'Upload a CSV or Excel file on the left sidebar first...'
              : isRecording
              ? 'Listening to your voice...'
              : 'Ask a question in Arabic or English (e.g. "What is total revenue by product?")...'
          }
          value={textPrompt}
          onChange={(e) => setTextPrompt(e.target.value)}
          disabled={isLoading || isRecording || !hasDataset}
        />

        <button
          type="submit"
          className="send-button"
          disabled={!textPrompt.trim() || isLoading || isRecording || !hasDataset}
          title="Send query"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
