import React, { useRef, useState } from 'react';
import { Session } from '../types';
import {
  MessageSquare,
  Plus,
  Trash2,
  UploadCloud,
  FileSpreadsheet,
  Layers,
  ChevronRight,
  Database,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (id: string) => void;
  onFileUpload: (file: File) => void;
  onLoadDemo: () => void;
  isUploading: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onFileUpload,
  onLoadDemo,
  isUploading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileUpload(files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <aside className="app-sidebar">
      <div className="sidebar-section-header">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">Analysis Sessions</span>
        </div>
        <button className="btn btn-primary btn-sm btn-icon" onClick={onCreateSession} title="Create New Session">
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="sessions-list">
        {sessions.length === 0 ? (
          <div className="empty-sessions">
            <p className="text-xs text-muted">No sessions yet.</p>
            <button className="btn btn-secondary btn-xs mt-2" onClick={onCreateSession}>
              <Plus className="w-3 h-3" /> New Session
            </button>
          </div>
        ) : (
          sessions.map((s) => {
            const isSelected = s.id === currentSessionId;
            return (
              <div
                key={s.id}
                className={`session-item ${isSelected ? 'active' : ''}`}
                onClick={() => onSelectSession(s.id)}
              >
                <div className="session-icon">
                  {s.file_name ? (
                    <FileSpreadsheet className="w-4 h-4 text-primary" />
                  ) : (
                    <MessageSquare className="w-4 h-4 text-muted" />
                  )}
                </div>
                <div className="session-info truncate">
                  <div className="session-title truncate">{s.title || 'Untitled Session'}</div>
                  <div className="session-subtext text-xs text-muted truncate">
                    {s.file_name ? `${s.row_count} rows • ${s.file_type}` : 'No dataset loaded'}
                  </div>
                </div>
                {isSelected && (
                  <button
                    className="session-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm('Delete this session?')) {
                        onDeleteSession(s.id);
                      }
                    }}
                    title="Delete Session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-upload-section">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".csv,.xlsx,.xls"
          style={{ display: 'none' }}
        />
        <div
          className={`upload-dropzone ${isDragOver ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadCloud className="w-6 h-6 upload-icon" />
          <div className="upload-text">
            {isUploading ? (
              <span className="text-primary font-medium">Ingesting Dataset...</span>
            ) : (
              <>
                <span className="font-medium text-sm">Upload CSV or Excel</span>
                <span className="text-xs text-muted">Drag & drop or browse</span>
              </>
            )}
          </div>
        </div>

        <button className="btn btn-ghost btn-xs w-full mt-2 justify-center" onClick={onLoadDemo}>
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>Load Bilingual Demo Data</span>
        </button>
      </div>
    </aside>
  );
};
