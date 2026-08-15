import os
import re
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from backend.config import SYSTEM_DB_PATH, DATABASES_DIR, UPLOADS_DIR, AUDIO_DIR

def get_system_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SYSTEM_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_system_db():
    conn = get_system_db()
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            file_name TEXT,
            file_type TEXT,
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Messages / Chat history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            audio_url TEXT,
            transcript TEXT,
            sql_query TEXT,
            query_result TEXT,
            chart_config TEXT,
            reasoning TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    # Dataset metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_metadata (
            session_id TEXT PRIMARY KEY,
            table_name TEXT NOT NULL DEFAULT 'dataset',
            columns_info TEXT NOT NULL,
            sample_rows TEXT NOT NULL,
            summary_stats TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize upon module import
init_system_db()

def get_session_db_path(session_id: str) -> Path:
    return DATABASES_DIR / f"{session_id}.db"

def clean_column_name(col_name: str) -> str:
    """Sanitize column name for clean SQLite identifier while preserving Arabic or English words."""
    col_str = str(col_name).strip()
    # Replace whitespace and punctuation with underscore
    sanitized = re.sub(r'[\s\-+*/\\%().,;:?!\'"`]+', '_', col_str)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip('_')
    if not sanitized or sanitized[0].isdigit():
        sanitized = f"col_{sanitized}"
    return sanitized

def create_session(session_id: str, title: str = "New Analysis Session") -> Dict[str, Any]:
    conn = get_system_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, title, now, now)
    )
    conn.commit()
    conn.close()
    return {
        "id": session_id,
        "title": title,
        "file_name": None,
        "file_type": None,
        "row_count": 0,
        "column_count": 0,
        "created_at": now,
        "updated_at": now,
    }

def list_sessions() -> List[Dict[str, Any]]:
    conn = get_system_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_system_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    session_data = dict(row)
    
    # Fetch dataset metadata
    cursor.execute("SELECT * FROM dataset_metadata WHERE session_id = ?", (session_id,))
    meta_row = cursor.fetchone()
    if meta_row:
        session_data["metadata"] = {
            "table_name": meta_row["table_name"],
            "columns": json.loads(meta_row["columns_info"]),
            "sample_rows": json.loads(meta_row["sample_rows"]),
            "summary_stats": json.loads(meta_row["summary_stats"]) if meta_row["summary_stats"] else {}
        }
    else:
        session_data["metadata"] = None
        
    # Fetch messages
    cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    msg_rows = cursor.fetchall()
    session_data["messages"] = []
    for m in msg_rows:
        msg_dict = dict(m)
        if msg_dict.get("query_result"):
            try:
                msg_dict["query_result"] = json.loads(msg_dict["query_result"])
            except Exception:
                pass
        if msg_dict.get("chart_config"):
            try:
                msg_dict["chart_config"] = json.loads(msg_dict["chart_config"])
            except Exception:
                pass
        session_data["messages"].append(msg_dict)
        
    conn.close()
    return session_data

def update_session_title(session_id: str, title: str):
    conn = get_system_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
    conn.commit()
    conn.close()

def delete_session(session_id: str):
    conn = get_system_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM dataset_metadata WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    
    # Delete SQLite DB file for this session
    db_path = get_session_db_path(session_id)
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

def add_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    audio_url: Optional[str] = None,
    transcript: Optional[str] = None,
    sql_query: Optional[str] = None,
    query_result: Optional[Any] = None,
    chart_config: Optional[Any] = None,
    reasoning: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_system_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    q_res_str = json.dumps(query_result, ensure_ascii=False) if query_result is not None else None
    chart_str = json.dumps(chart_config, ensure_ascii=False) if chart_config is not None else None
    
    cursor.execute("""
        INSERT INTO messages (
            id, session_id, role, content, audio_url, transcript,
            sql_query, query_result, chart_config, reasoning, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message_id, session_id, role, content, audio_url, transcript,
        sql_query, q_res_str, chart_str, reasoning, now
    ))
    
    cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()
    
    return {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "audio_url": audio_url,
        "transcript": transcript,
        "sql_query": sql_query,
        "query_result": query_result,
        "chart_config": chart_config,
        "reasoning": reasoning,
        "created_at": now
    }

def ingest_dataset(session_id: str, file_path: Path, original_filename: str) -> Dict[str, Any]:
    """
    Ingests a CSV or Excel file into the session SQLite database,
    normalizes columns, and computes schema + sample metadata.
    """
    ext = file_path.suffix.lower()
    df: pd.DataFrame
    
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    elif ext == ".csv":
        # Try common encodings
        for enc in ["utf-8", "utf-8-sig", "latin1", "cp1256", "iso-8859-1"]:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except Exception:
                continue
        else:
            df = pd.read_csv(file_path, errors="replace")
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please upload CSV or Excel.")

    # Remove completely empty rows/columns
    df = df.dropna(how="all").dropna(axis=1, how="all")
    
    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    # Build column mapping & metadata
    col_mapping = {}
    columns_info = []
    used_names = set()
    
    for col in df.columns:
        orig_name = str(col).strip()
        sql_col = clean_column_name(orig_name)
        
        # Ensure unique SQL column names
        base_name = sql_col
        counter = 1
        while sql_col in used_names:
            sql_col = f"{base_name}_{counter}"
            counter += 1
        used_names.add(sql_col)
        col_mapping[col] = sql_col
        
        series = df[col]
        # Inferred type
        if pd.api.types.is_integer_dtype(series):
            inferred_type = "INTEGER"
        elif pd.api.types.is_float_dtype(series):
            inferred_type = "REAL"
        elif pd.api.types.is_datetime64_any_dtype(series):
            inferred_type = "DATETIME"
        elif pd.api.types.is_bool_dtype(series):
            inferred_type = "BOOLEAN"
        else:
            inferred_type = "TEXT"
            
        # Get representative unique sample values
        non_null_samples = series.dropna().unique()
        sample_vals = [str(v) for v in non_null_samples[:5]]
        
        columns_info.append({
            "original_name": orig_name,
            "sql_name": sql_col,
            "type": inferred_type,
            "null_count": int(series.isnull().sum()),
            "distinct_count": int(series.nunique()),
            "sample_values": sample_vals
        })

    # Rename dataframe columns to sanitized SQL column names
    df_clean = df.rename(columns=col_mapping)
    
    # Extract first 5 sample rows as dictionary
    sample_rows = df_clean.head(5).to_dict(orient="records")
    # Clean NaN / NaT in sample rows for clean JSON serialization
    for row in sample_rows:
        for k, v in row.items():
            if pd.isna(v):
                row[k] = None
            elif hasattr(v, "isoformat"):
                row[k] = v.isoformat()

    # Compute summary statistics
    summary_stats = {
        "total_rows": int(len(df_clean)),
        "total_columns": int(len(df_clean.columns)),
        "numeric_columns": [c["sql_name"] for c in columns_info if c["type"] in ["INTEGER", "REAL"]],
        "categorical_columns": [c["sql_name"] for c in columns_info if c["type"] == "TEXT" and c["distinct_count"] <= 50],
        "date_columns": [c["sql_name"] for c in columns_info if c["type"] == "DATETIME"]
    }

    # Store into session SQLite database file
    db_path = get_session_db_path(session_id)
    # Remove existing session db if any
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
            
    conn_session = sqlite3.connect(str(db_path))
    # Write dataframe to table 'dataset'
    df_clean.to_sql("dataset", conn_session, if_exists="replace", index=False)
    
    # Create indexes for columns with moderate distinct count to speed up queries
    cursor = conn_session.cursor()
    for col in columns_info:
        if col["distinct_count"] > 1 and col["distinct_count"] < 10000:
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{col["sql_name"]} ON dataset ("{col["sql_name"]}")')
            except Exception:
                pass
    conn_session.commit()
    conn_session.close()

    # Update system metadata
    conn_sys = get_system_db()
    cur_sys = conn_sys.cursor()
    now = datetime.utcnow().isoformat()
    
    cur_sys.execute("""
        INSERT INTO dataset_metadata (session_id, table_name, columns_info, sample_rows, summary_stats, updated_at)
        VALUES (?, 'dataset', ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            table_name = 'dataset',
            columns_info = excluded.columns_info,
            sample_rows = excluded.sample_rows,
            summary_stats = excluded.summary_stats,
            updated_at = excluded.updated_at
    """, (
        session_id,
        json.dumps(columns_info, ensure_ascii=False),
        json.dumps(sample_rows, ensure_ascii=False),
        json.dumps(summary_stats, ensure_ascii=False),
        now
    ))
    
    cur_sys.execute("""
        UPDATE sessions SET
            file_name = ?,
            file_type = ?,
            row_count = ?,
            column_count = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        original_filename,
        ext.replace(".", "").upper(),
        len(df_clean),
        len(df_clean.columns),
        now,
        session_id
    ))
    
    conn_sys.commit()
    conn_sys.close()

    return {
        "session_id": session_id,
        "table_name": "dataset",
        "file_name": original_filename,
        "row_count": len(df_clean),
        "column_count": len(df_clean.columns),
        "columns": columns_info,
        "sample_rows": sample_rows,
        "summary_stats": summary_stats
    }

def execute_session_query(session_id: str, sql_query: str, max_rows: int = 1000) -> Dict[str, Any]:
    """
    Executes a SELECT query on the session dataset SQLite database.
    """
    db_path = get_session_db_path(session_id)
    if not db_path.exists():
        raise FileNotFoundError(f"No dataset found for session {session_id}. Please upload a CSV or Excel file first.")

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Enforce safe read-only pragma query config
    cursor.execute("PRAGMA query_only = ON;")
    
    cursor.execute(sql_query)
    rows_raw = cursor.fetchmany(max_rows)
    
    columns = [description[0] for description in cursor.description] if cursor.description else []
    
    rows = []
    for r in rows_raw:
        row_dict = {}
        for col in columns:
            val = r[col]
            # Convert bytes / unsupported types
            if isinstance(val, bytes):
                try:
                    val = val.decode("utf-8", errors="replace")
                except Exception:
                    val = str(val)
            row_dict[col] = val
        rows.append(row_dict)
        
    conn.close()
    
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) >= max_rows
    }
