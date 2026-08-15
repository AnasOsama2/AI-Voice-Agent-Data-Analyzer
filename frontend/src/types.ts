export interface ColumnInfo {
  original_name: string;
  sql_name: string;
  type: string; // INTEGER | REAL | TEXT | DATETIME | BOOLEAN
  null_count: number;
  distinct_count: number;
  sample_values: string[];
}

export interface SummaryStats {
  total_rows?: number;
  total_columns?: number;
  numeric_columns?: string[];
  categorical_columns?: string[];
  date_columns?: string[];
}

export interface DatasetMetadata {
  table_name: string;
  columns: ColumnInfo[];
  sample_rows: Record<string, any>[];
  summary_stats: SummaryStats;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  truncated?: boolean;
}

export interface ChartConfig {
  chart_type: 'bar' | 'line' | 'area' | 'pie' | 'metric_card' | 'table_only';
  title?: string;
  x_key?: string;
  y_keys?: string[];
  color?: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  audio_url?: string;
  transcript?: string;
  sql_query?: string;
  query_result?: QueryResult;
  chart_config?: ChartConfig;
  reasoning?: string;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  file_name?: string;
  file_type?: string;
  row_count: number;
  column_count: number;
  created_at: string;
  updated_at: string;
  metadata?: DatasetMetadata;
  messages?: Message[];
}
