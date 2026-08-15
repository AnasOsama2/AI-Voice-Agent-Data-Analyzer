import React from 'react';
import { Session } from '../types';
import { Database, Sparkles, FileSpreadsheet, Eye, Info } from 'lucide-react';

interface HeaderProps {
  currentSession: Session | null;
  onOpenSchemaModal: () => void;
  onLoadDemo: () => void;
  isBackendHealthy: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentSession,
  onOpenSchemaModal,
  onLoadDemo,
  isBackendHealthy,
}) => {
  const metadata = currentSession?.metadata;
  const hasData = Boolean(metadata && currentSession?.file_name);

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-icon-wrapper">
          <svg className="brand-logo" viewBox="0 0 24 24" fill="none">
            <rect x="9" y="2" width="6" height="12" rx="3" fill="url(#headerGrad)" />
            <path d="M5 10v1a7 7 0 0 0 14 0v-1" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
            <line x1="12" y1="18" x2="12" y2="22" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
            <line x1="8" y1="22" x2="16" y2="22" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
            <defs>
              <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#a855f7" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="brand-info">
          <div className="brand-title-row">
            <h1 className="brand-title">VoiceData AI</h1>
            <span className="badge badge-primary">Voice + SQL</span>
          </div>
          <p className="brand-subtitle">Autonomous Bilingual Data Analytics Agent</p>
        </div>
      </div>

      <div className="header-center">
        {hasData && (
          <div className="dataset-status-pill animate-fade-in">
            <FileSpreadsheet className="w-4 h-4 text-primary" />
            <span className="dataset-name truncate" title={currentSession.file_name}>
              {currentSession.file_name}
            </span>
            <span className="dataset-meta-badge">
              {currentSession.row_count?.toLocaleString()} rows
            </span>
            <span className="dataset-meta-badge">
              {currentSession.column_count} cols
            </span>
            <button
              className="btn btn-ghost btn-xs"
              onClick={onOpenSchemaModal}
              title="Inspect dataset schema and sample rows"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Inspect</span>
            </button>
          </div>
        )}
      </div>

      <div className="header-actions">
        {!hasData && (
          <button className="btn btn-secondary btn-sm" onClick={onLoadDemo} title="Load sample dataset">
            <Sparkles className="w-4 h-4 text-accent" />
            <span>Load Demo Dataset</span>
          </button>
        )}

        <div className={`health-indicator ${isBackendHealthy ? 'healthy' : 'warning'}`} title={isBackendHealthy ? 'Backend Connected (Groq AI Ready)' : 'Connecting to API...'}>
          <span className="health-dot"></span>
          <span className="health-label">{isBackendHealthy ? 'Groq LPU Active' : 'Connecting...'}</span>
        </div>
      </div>
    </header>
  );
};
