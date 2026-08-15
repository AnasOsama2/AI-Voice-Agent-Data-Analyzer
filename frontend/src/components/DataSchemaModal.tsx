import React from 'react';
import { DatasetMetadata } from '../types';
import { X, Database, Columns, FileSpreadsheet, Hash } from 'lucide-react';

interface DataSchemaModalProps {
  metadata: DatasetMetadata | null;
  fileName?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const DataSchemaModal: React.FC<DataSchemaModalProps> = ({
  metadata,
  fileName,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !metadata) return null;

  const columns = metadata.columns || [];
  const sampleRows = metadata.sample_rows || [];
  const summary = metadata.summary_stats || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Database size={20} color="#6366f1" />
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                Dataset Schema & Context Sample
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {fileName || 'Active Dataset'} • Table: <code>{metadata.table_name}</code> •{' '}
                {summary.total_rows ?? sampleRows.length} Rows • {columns.length} Columns
              </p>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* 1. Columns & Data Types */}
          <div>
            <h4
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                marginBottom: 10,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Columns size={16} color="#38bdf8" />
              <span>Column Definitions & Data Types</span>
            </h4>
            <div className="data-table-container" style={{ maxHeight: 200 }}>
              <table className="styled-table">
                <thead>
                  <tr>
                    <th>Original Name</th>
                    <th>SQL Identifier</th>
                    <th>Inferred Type</th>
                    <th>Distinct Values</th>
                    <th>Sample Distinct Values</th>
                  </tr>
                </thead>
                <tbody>
                  {columns.map((c) => (
                    <tr key={c.sql_name}>
                      <td style={{ fontWeight: 600 }}>{c.original_name}</td>
                      <td>
                        <code style={{ color: '#38bdf8' }}>{c.sql_name}</code>
                      </td>
                      <td>
                        <span
                          style={{
                            padding: '2px 6px',
                            borderRadius: 4,
                            background:
                              c.type === 'INTEGER' || c.type === 'REAL'
                                ? 'rgba(16, 185, 129, 0.15)'
                                : c.type === 'DATETIME'
                                ? 'rgba(245, 158, 11, 0.15)'
                                : 'rgba(99, 102, 241, 0.15)',
                            color:
                              c.type === 'INTEGER' || c.type === 'REAL'
                                ? '#10b981'
                                : c.type === 'DATETIME'
                                ? '#f59e0b'
                                : '#818cf8',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                          }}
                        >
                          {c.type}
                        </span>
                      </td>
                      <td>{c.distinct_count}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        {c.sample_values?.slice(0, 4).join(', ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 2. First 5 Representative Rows Sample */}
          <div>
            <h4
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                marginBottom: 10,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <FileSpreadsheet size={16} color="#10b981" />
              <span>First 5 Sample Rows (Agent Context)</span>
            </h4>
            <div className="data-table-container" style={{ maxHeight: 220 }}>
              <table className="styled-table">
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>#</th>
                    {columns.map((c) => (
                      <th key={c.sql_name}>{c.sql_name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sampleRows.map((row, idx) => (
                    <tr key={idx}>
                      <td style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{idx + 1}</td>
                      {columns.map((c) => (
                        <td key={c.sql_name}>
                          {row[c.sql_name] !== null && row[c.sql_name] !== undefined
                            ? String(row[c.sql_name])
                            : 'NULL'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
