import os
import re
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from groq import Groq
from backend.config import GROQ_API_KEY, WHISPER_MODEL, LLM_MODEL, AUDIO_DIR
from backend.database import get_session, execute_session_query
from backend.sql_safety import validate_and_sanitize_sql

def get_groq_client() -> Groq:
    if not GROQ_API_KEY:
        raise ValueError("Groq API Key is not set in environment or .env file.")
    return Groq(api_key=GROQ_API_KEY)

def transcribe_audio(audio_file_path: Path) -> Dict[str, Any]:
    """
    Transcribes audio using Groq Whisper-large-v3-turbo model.
    Supports English, Arabic, and multilingual voice inputs.
    """
    client = get_groq_client()
    with open(audio_file_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(audio_file_path.name, f),
            model=WHISPER_MODEL,
            response_format="verbose_json",
            temperature=0.0
        )
    
    # transcription is a Translation or Transcription object
    transcript_text = getattr(transcription, "text", "") or ""
    language = getattr(transcription, "language", "en") or "en"
    duration = getattr(transcription, "duration", 0.0) or 0.0
    
    return {
        "text": transcript_text.strip(),
        "language": language,
        "duration": duration
    }

def detect_language(text: str) -> str:
    """Detect if the input text is primarily Arabic or English."""
    arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
    total_alpha = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text))
    if total_alpha > 0 and (arabic_chars / total_alpha) > 0.3:
        return "ar"
    return "en"

def build_schema_context(metadata: Dict[str, Any]) -> str:
    """Constructs detailed schema and 5-row sample context for the LLM."""
    table_name = metadata.get("table_name", "dataset")
    columns = metadata.get("columns", [])
    sample_rows = metadata.get("sample_rows", [])
    summary_stats = metadata.get("summary_stats", {})
    
    cols_desc = []
    for c in columns:
        sample_str = ", ".join([f'"{v}"' for v in c.get("sample_values", [])[:4]])
        cols_desc.append(
            f"- SQL Column: `{c['sql_name']}` (Type: {c['type']}, Original Name: \"{c['original_name']}\")\n"
            f"  Null Count: {c.get('null_count', 0)}, Distinct Values: {c.get('distinct_count', 0)}\n"
            f"  Sample Values: [{sample_str}]"
        )
    
    cols_block = "\n".join(cols_desc)
    sample_rows_json = json.dumps(sample_rows, indent=2, ensure_ascii=False)
    
    return f"""### Database Information:
- Table Name: `{table_name}`
- Total Rows: {summary_stats.get('total_rows', 'Unknown')}
- Total Columns: {summary_stats.get('total_columns', len(columns))}

### Column Schema & Representative Values:
{cols_block}

### First 5 Representative Sample Rows:
```json
{sample_rows_json}
```
"""

def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON object from LLM response (checks clean text and raw text)."""
    if not text:
        return None
        
    # 1. Clean thinking tags if present
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    candidates = [cleaned, text]
    
    for candidate in candidates:
        if not candidate:
            continue
        # Try finding markdown json code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', candidate, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except Exception:
                pass
                
        # Try direct parse
        try:
            return json.loads(candidate)
        except Exception:
            pass
            
        # Search from first { to last }
        first_brace = candidate.find('{')
        last_brace = candidate.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(candidate[first_brace:last_brace+1])
            except Exception:
                pass
                
    return None

def extract_sql_from_text(text: str) -> Optional[str]:
    """Robust extractor for SQLite SELECT query from text, reasoning, or markdown."""
    if not text:
        return None
        
    patterns = [
        r'```(?:sql)?\s*((?:SELECT|WITH\s+[a-zA-Z0-9_]+\s+AS)\b.*?)\s*```',
        r'(?:Final\s+)?SQL\s*:\s*`?((?:SELECT|WITH\s+[a-zA-Z0-9_]+\s+AS)\s+.*?)(?:`|\n\n|\n[A-Z\u0600-\u06FF]|$)',
        r'\b(SELECT\s+.*?\bFROM\s+dataset\b.*?)(?:;|\n\n|```|$)'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
        for m in matches:
            candidate = m.group(1).strip().rstrip(';').strip('`')
            is_safe, san_sql, _ = validate_and_sanitize_sql(candidate)
            if is_safe and san_sql:
                return san_sql
                
    return None

def extract_reasoning_and_content(text: str) -> Tuple[Optional[str], str]:
    """Extracts <think>...</think> reasoning and the remaining response content."""
    reasoning_match = re.search(r'<think>(.*?)(?:</think>|$)', text, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else None
    content = re.sub(r'<think>.*?(?:</think>|$)', '', text, flags=re.DOTALL).strip()
    return reasoning, content

def generate_sql_query(
    user_prompt: str,
    metadata: Dict[str, Any],
    chat_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Uses Qwen 3.6-27B to analyze user intent and generate a safe SQLite query.
    """
    client = get_groq_client()
    schema_context = build_schema_context(metadata)
    lang = detect_language(user_prompt)
    
    system_prompt = f"""You are an expert Data Analyst and SQLite Specialist AI.
Your task is to analyze user questions (which may be in Arabic or English) and generate an accurate, safe SQLite query against the user's dataset table named `dataset`.

{schema_context}

### Rules for SQL Generation:
1. Generate STRICTLY a single SQLite SELECT query (or WITH CTE followed by SELECT).
2. NEVER generate UPDATE, DELETE, DROP, INSERT, ALTER, CREATE, ATTACH, PRAGMA, or multi-statement queries.
3. Use exact SQL column names as defined in the schema.
4. For text searches or filter values, use `LIKE '%value%'` (case-insensitive where needed) or exact matching.
5. If calculating top/bottom items, use `ORDER BY <metric> DESC/ASC LIMIT <n>`.
6. Provide meaningful aliases for aggregated columns (e.g., `SUM(revenue) AS total_revenue`, `COUNT(*) AS count_students`).
7. For percentage / threshold calculations, inspect column ranges and sample values.
8. KEEP YOUR REASONING CONCISE (max 3-5 lines).
9. Output MUST be strictly in valid JSON format outside any thinking tags:
```json
{{
  "thought_process": "Brief explanation of how the columns and query logic solve the user request",
  "sql": "SELECT ... FROM dataset ...",
  "intent": "Brief summary of the analysis"
}}
```
If the question does not require a database query, set `"sql": null` and explain in `"thought_process"`.
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Append recent chat history for context (up to 4 previous messages)
    for msg in chat_history[-4:]:
        if msg.get("role") in ["user", "assistant"]:
            content = msg.get("content", "")
            if msg.get("transcript"):
                content = f"[Voice Transcript]: {msg['transcript']}"
            messages.append({"role": msg["role"], "content": content})
            
    messages.append({"role": "user", "content": user_prompt})
    
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_completion_tokens=2048
    )
    
    raw_response = response.choices[0].message.content or ""
    reasoning, clean_text = extract_reasoning_and_content(raw_response)
    
    # Try parsing JSON from clean_text, then raw_response
    parsed = extract_json_block(clean_text) or extract_json_block(raw_response)
    if parsed and "sql" in parsed and parsed.get("sql"):
        return {
            "sql": parsed.get("sql"),
            "intent": parsed.get("intent", user_prompt),
            "thought_process": parsed.get("thought_process", ""),
            "reasoning": reasoning
        }
    
    # Fallback SQL extraction across clean_text, raw_response, and reasoning
    sql_candidate = (
        extract_sql_from_text(clean_text) or 
        extract_sql_from_text(raw_response) or 
        extract_sql_from_text(reasoning or "")
    )
    
    if sql_candidate:
        return {
            "sql": sql_candidate,
            "intent": user_prompt,
            "thought_process": clean_text or "Extracted SQL query from reasoning model output.",
            "reasoning": reasoning
        }
        
    return {
        "sql": None,
        "intent": user_prompt,
        "thought_process": clean_text,
        "reasoning": reasoning
    }

def explain_and_recommend_charts(
    user_prompt: str,
    sql_query: str,
    query_result: Dict[str, Any],
    metadata: Dict[str, Any],
    lang: str = "en"
) -> Dict[str, Any]:
    """
    Sends executed query results back to Qwen 3.6-27B to synthesize a comprehensive bilingual
    answer, key insights, and dynamic chart configuration.
    """
    client = get_groq_client()
    
    columns = query_result.get("columns", [])
    rows = query_result.get("rows", [])
    row_count = query_result.get("row_count", 0)
    
    # Truncate rows passed to LLM for context efficiency (max 30 rows)
    llm_rows_sample = rows[:30]
    
    result_preview = {
        "columns": columns,
        "total_rows_returned": row_count,
        "sample_data": llm_rows_sample
    }
    
    target_lang = "Arabic (العربية)" if lang == "ar" else "English"
    
    system_prompt = f"""You are an elite Business Intelligence and Data Analyst AI.
The user asked a data question, the database was queried via SQLite, and here are the execution results.

Your task is to:
1. Provide a clear, insightful, direct explanation answering the user's question.
2. Formulate your response in **{target_lang}**. If the user prompt was in Arabic, write in elegant, professional Arabic with proper analytical formatting.
3. Recommend the best visual chart type to represent these results (e.g. `bar`, `line`, `area`, `pie`, `metric_card`, or `table_only`).
4. Output MUST be formatted as a valid JSON object matching this schema:

```json
{{
  "answer": "Clear, markdown-formatted narrative explanation of the results, highlighting specific figures and percentages.",
  "key_insights": [
    "Key takeaway point 1",
    "Key takeaway point 2"
  ],
  "chart_config": {{
    "chart_type": "bar | line | area | pie | metric_card | table_only",
    "title": "Descriptive Chart Title",
    "x_key": "name_of_column_for_x_axis",
    "y_keys": ["name_of_column_for_values"],
    "color": "#6366f1"
  }}
}}
```

### Chart Guidelines:
- If there's 1 categorical/date column and 1-3 numeric columns, `bar` or `line` is best.
- If there's a trend over time/dates, use `line` or `area`.
- If showing parts of a whole (under 8 categories), use `pie`.
- If the result is a single single number/row summary, use `metric_card`.
- If the result is a raw list or complex table not suitable for simple charts, use `table_only`.
"""

    user_message = f"""User Request: {user_prompt}
Executed SQL: {sql_query}
Query Results:
{json.dumps(result_preview, indent=2, ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        max_completion_tokens=2048
    )
    
    raw_response = response.choices[0].message.content or ""
    reasoning, clean_text = extract_reasoning_and_content(raw_response)
    parsed = extract_json_block(clean_text) or extract_json_block(raw_response)
    
    if parsed and "answer" in parsed:
        return {
            "answer": parsed.get("answer", ""),
            "key_insights": parsed.get("key_insights", []),
            "chart_config": parsed.get("chart_config", {"chart_type": "table_only"}),
            "reasoning": reasoning
        }
        
    return {
        "answer": clean_text or raw_response,
        "key_insights": [],
        "chart_config": {"chart_type": "table_only", "title": "Query Results"},
        "reasoning": reasoning
    }

def run_agent_pipeline(
    session_id: str,
    user_prompt: Optional[str] = None,
    audio_file_path: Optional[Path] = None,
    chat_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Full end-to-end AI Agent pipeline:
    1. STT via Groq Whisper-large-v3-turbo (if audio provided).
    2. Retrieve session schema & 5-row sample.
    3. Generate SQL query via Qwen 3.6-27B.
    4. SQL safety validation & execution.
    5. Result synthesis, bilingual explanation & chart recommendation.
    """
    start_time = time.time()
    chat_history = chat_history or []
    
    # 1. Transcribe audio if provided
    transcript_info = None
    if audio_file_path:
        transcript_info = transcribe_audio(audio_file_path)
        prompt_text = transcript_info["text"]
    else:
        prompt_text = (user_prompt or "").strip()
        
    if not prompt_text:
        raise ValueError("No voice transcript or text query received.")
        
    lang = detect_language(prompt_text)
    
    # 2. Get session & metadata
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found.")
        
    metadata = session.get("metadata")
    if not metadata:
        return {
            "prompt": prompt_text,
            "transcript": transcript_info["text"] if transcript_info else None,
            "audio_url": None,
            "sql_query": None,
            "query_result": None,
            "chart_config": None,
            "answer": "يرجى رفع ملف بيانات (CSV أو Excel) أولاً لبدء التحليل." if lang == "ar" else "Please upload a CSV or Excel dataset first to start analyzing.",
            "key_insights": [],
            "reasoning": None,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }
        
    # 3. Generate SQL Query
    gen_result = generate_sql_query(prompt_text, metadata, chat_history)
    sql_query = gen_result.get("sql")
    reasoning_sql = gen_result.get("reasoning")
    
    if not sql_query:
        return {
            "prompt": prompt_text,
            "transcript": transcript_info["text"] if transcript_info else None,
            "audio_url": None,
            "sql_query": None,
            "query_result": None,
            "chart_config": None,
            "answer": gen_result.get("thought_process") or ("لم أتمكن من استخراج استعلام مناسب." if lang == "ar" else "I could not formulate an appropriate SQL query for this request."),
            "key_insights": [],
            "reasoning": reasoning_sql,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }
        
    # 4. Validate SQL Safety
    is_safe, sanitized_sql, error_msg = validate_and_sanitize_sql(sql_query)
    if not is_safe:
        return {
            "prompt": prompt_text,
            "transcript": transcript_info["text"] if transcript_info else None,
            "audio_url": None,
            "sql_query": sql_query,
            "query_result": None,
            "chart_config": None,
            "answer": f"⚠️ تم حظر الاستعلام لأسباب أمنية: {error_msg}" if lang == "ar" else f"⚠️ Query blocked by safety validator: {error_msg}",
            "key_insights": [],
            "reasoning": reasoning_sql,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }
        
    # 5. Execute SQL Query
    try:
        query_result = execute_session_query(session_id, sanitized_sql)
    except Exception as e:
        # Self-correction attempt: prompt Qwen to fix SQL error once
        error_details = str(e)
        repair_prompt = f"The generated SQL `{sanitized_sql}` failed with error: `{error_details}`. Fix the SQLite query to answer: {prompt_text}"
        fixed_gen = generate_sql_query(repair_prompt, metadata, chat_history)
        if fixed_gen.get("sql") and fixed_gen.get("sql") != sanitized_sql:
            is_safe_fixed, fixed_sql, _ = validate_and_sanitize_sql(fixed_gen["sql"])
            if is_safe_fixed:
                try:
                    query_result = execute_session_query(session_id, fixed_sql)
                    sanitized_sql = fixed_sql
                except Exception as e2:
                    return {
                        "prompt": prompt_text,
                        "transcript": transcript_info["text"] if transcript_info else None,
                        "audio_url": None,
                        "sql_query": sanitized_sql,
                        "query_result": None,
                        "chart_config": None,
                        "answer": f"حدث خطأ أثناء تنفيذ الاستعلام: {str(e2)}" if lang == "ar" else f"Database query execution error: {str(e2)}",
                        "key_insights": [],
                        "reasoning": reasoning_sql,
                        "execution_time_ms": int((time.time() - start_time) * 1000)
                    }
            else:
                return {
                    "prompt": prompt_text,
                    "transcript": transcript_info["text"] if transcript_info else None,
                    "audio_url": None,
                    "sql_query": sanitized_sql,
                    "query_result": None,
                    "chart_config": None,
                    "answer": f"حدث خطأ أثناء تنفيذ الاستعلام: {error_details}" if lang == "ar" else f"Database query execution error: {error_details}",
                    "key_insights": [],
                    "reasoning": reasoning_sql,
                    "execution_time_ms": int((time.time() - start_time) * 1000)
                }
        else:
            return {
                "prompt": prompt_text,
                "transcript": transcript_info["text"] if transcript_info else None,
                "audio_url": None,
                "sql_query": sanitized_sql,
                "query_result": None,
                "chart_config": None,
                "answer": f"حدث خطأ أثناء تنفيذ الاستعلام: {error_details}" if lang == "ar" else f"Database query execution error: {error_details}",
                "key_insights": [],
                "reasoning": reasoning_sql,
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    # 6. LLM Explanation & Chart Config
    synth = explain_and_recommend_charts(prompt_text, sanitized_sql, query_result, metadata, lang)
    
    total_time = int((time.time() - start_time) * 1000)
    
    return {
        "prompt": prompt_text,
        "transcript": transcript_info["text"] if transcript_info else None,
        "audio_url": None,
        "sql_query": sanitized_sql,
        "query_result": query_result,
        "chart_config": synth.get("chart_config"),
        "answer": synth.get("answer"),
        "key_insights": synth.get("key_insights", []),
        "reasoning": synth.get("reasoning") or reasoning_sql,
        "execution_time_ms": total_time
    }
