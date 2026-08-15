import React, { useState } from 'react';
import { Message } from '../types';
import { ChartRenderer } from './ChartRenderer';
import {
  Bot,
  User,
  Terminal,
  ChevronDown,
  ChevronUp,
  Table,
  BarChart2,
  Volume2,
  CheckCircle2,
  Clock,
  Sparkles,
  Lightbulb,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [showSQL, setShowSQL] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const [showReasoning, setShowReasoning] = useState(false);

  const queryResult = message.query_result;
  const chartConfig = message.chart_config;
  const hasChart = Boolean(
    chartConfig && chartConfig.chart_type && chartConfig.chart_type !== 'table_only'
  );
  const hasTable = Boolean(queryResult && queryResult.rows && queryResult.rows.length > 0);

  return (
    <div className={`chat-message-row ${isUser ? 'user-row' : 'assistant-row'} animate-fade-in`}>
      <div className={`message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content-wrapper">
        {/* User Bubble */}
        {isUser ? (
          <div className="user-bubble">
            {message.transcript && message.audio_url && (
              <div className="voice-badge">
                <Volume2 size={13} />
                <span>Voice Query</span>
              </div>
            )}
            <p className="user-text">{message.content}</p>
          </div>
        ) : (
          /* Assistant Card */
          <div className="assistant-card">
            {/* 1. Main Narrative Explanation */}
            <div className="assistant-narrative prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>

            {/* 2. Key Insights Badges */}
            {message.reasoning && (
              <div className="collapsible-section">
                <button
                  className="collapsible-toggle"
                  onClick={() => setShowReasoning(!showReasoning)}
                >
                  <Sparkles size={14} color="#a855f7" />
                  <span className="font-semibold text-xs">AI Reasoning Thought Process</span>
                  {showReasoning ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                {showReasoning && (
                  <div className="collapsible-content font-mono text-xs reasoning-box">
                    {message.reasoning}
                  </div>
                )}
              </div>
            )}

            {/* 3. Generated & Validated SQL Query Box */}
            {message.sql_query && (
              <div className="sql-box">
                <div className="sql-box-header">
                  <div className="flex items-center gap-1.5">
                    <Terminal size={14} color="#38bdf8" />
                    <span className="sql-box-title font-mono text-xs">Verified Safe SQL</span>
                  </div>
                  <button
                    className="btn btn-ghost btn-xs"
                    onClick={() => setShowSQL(!showSQL)}
                    title="Toggle full SQL view"
                  >
                    {showSQL ? 'Collapse' : 'Expand SQL'}
                  </button>
                </div>
                <div className={`sql-code-container ${showSQL ? 'expanded' : 'collapsed'}`}>
                  <pre className="sql-code">
                    <code>{message.sql_query}</code>
                  </pre>
                </div>
              </div>
            )}

            {/* 4. Interactive Dynamic Chart Visualization */}
            {hasChart && queryResult && (
              <div className="chart-wrapper">
                <ChartRenderer
                  data={queryResult.rows}
                  config={chartConfig!}
                  columns={queryResult.columns}
                />
              </div>
            )}

            {/* 5. Tabular Data Result Toggle */}
            {hasTable && (
              <div className="collapsible-section mt-3">
                <button
                  className="collapsible-toggle"
                  onClick={() => setShowTable(!showTable)}
                >
                  <Table size={14} color="#10b981" />
                  <span className="font-semibold text-xs">
                    Result Dataset ({queryResult!.row_count} rows)
                  </span>
                  {showTable ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>

                {showTable && (
                  <div className="collapsible-content data-table-container">
                    <table className="styled-table">
                      <thead>
                        <tr>
                          {queryResult!.columns.map((col) => (
                            <th key={col}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {queryResult!.rows.slice(0, 100).map((row, rIdx) => (
                          <tr key={rIdx}>
                            {queryResult!.columns.map((col) => (
                              <td key={col}>
                                {row[col] !== null && row[col] !== undefined
                                  ? String(row[col])
                                  : 'NULL'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {queryResult!.row_count > 100 && (
                      <div className="table-footer-hint">
                        Showing first 100 of {queryResult!.row_count} rows
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
