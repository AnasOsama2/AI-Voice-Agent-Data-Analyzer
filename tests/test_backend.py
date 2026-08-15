import sys
import os
from pathlib import Path

# Ensure root in sys.path and UTF-8 output
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.database import create_session, get_session, ingest_dataset, execute_session_query
from backend.sql_safety import validate_and_sanitize_sql
from backend.agent import run_agent_pipeline

def run_tests():
    print("=== 1. Testing SQL Safety Validator ===")
    safe_queries = [
        "SELECT * FROM dataset LIMIT 5",
        "SELECT Region, SUM(Total_Revenue) as rev FROM dataset GROUP BY Region ORDER BY rev DESC",
        "WITH cte AS (SELECT * FROM dataset WHERE Units_Sold > 10) SELECT * FROM cte"
    ]
    for q in safe_queries:
        is_safe, san, err = validate_and_sanitize_sql(q)
        assert is_safe, f"Expected safe for: {q}, got error: {err}"
        print(f"  [PASS] Safe query valid: {san[:50]}...")

    dangerous_queries = [
        "DROP TABLE dataset",
        "SELECT * FROM dataset; DROP TABLE dataset;",
        "UPDATE dataset SET Total_Revenue = 0",
        "DELETE FROM dataset WHERE 1=1",
        "ATTACH DATABASE 'evil.db' AS evil"
    ]
    for q in dangerous_queries:
        is_safe, san, err = validate_and_sanitize_sql(q)
        assert not is_safe, f"Expected dangerous query to be blocked: {q}"
        print(f"  [PASS] Blocked malicious query: {q} -> {err}")

    print("\n=== 2. Testing Session Ingestion ===")
    import uuid
    session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    create_session(session_id, "Automated Test Session")
    
    csv_content = """Region,المنطقة,Product,المنتج,Revenue,Units
Riyadh,الرياض,Laptop,حاسوب,12000,10
Jeddah,جدة,Phone,هاتف,8500,15
Dammam,الدمام,Tablet,لوحي,4300,8
Riyadh,الرياض,Headphones,سماعات,1500,20
Jeddah,جدة,Screen,شاشة,6000,12
Dammam,الدمام,Laptop,حاسوب,14000,11
"""
    test_file = Path("backend/storage/uploads/test_data.csv")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(csv_content)
        
    meta = ingest_dataset(session_id, test_file, "test_data.csv")
    assert meta["row_count"] == 6, f"Expected 6 rows, got {meta['row_count']}"
    assert len(meta["sample_rows"]) == 5, f"Expected 5 sample rows, got {len(meta['sample_rows'])}"
    print(f"  [PASS] Dataset ingested with {meta['row_count']} rows, sample: {len(meta['sample_rows'])} rows")

    print("\n=== 3. Testing SQLite Direct Query ===")
    res = execute_session_query(session_id, "SELECT Region, SUM(Revenue) as total_rev FROM dataset GROUP BY Region")
    assert len(res["rows"]) == 3, f"Expected 3 regions, got {len(res['rows'])}"
    print(f"  [PASS] Query returned {len(res['rows'])} rows: {res['rows']}")

    print("\n=== 4. Testing AI Agent Pipeline (English Query) ===")
    ai_res_en = run_agent_pipeline(
        session_id=session_id,
        user_prompt="Which region generated the highest total revenue?"
    )
    print("  AI Response (EN):", ai_res_en.get("answer"))
    print("  Generated SQL:", ai_res_en.get("sql_query"))
    print("  Chart Config:", ai_res_en.get("chart_config"))
    assert ai_res_en.get("sql_query") is not None
    assert ai_res_en.get("query_result") is not None

    print("\n=== 5. Testing AI Agent Pipeline (Arabic Query) ===")
    ai_res_ar = run_agent_pipeline(
        session_id=session_id,
        user_prompt="ما هو إجمالي الإيرادات لكل منتج مرتبة من الأعلى إلى الأقل؟"
    )
    print("  AI Response (AR):", ai_res_ar.get("answer"))
    print("  Generated SQL (AR):", ai_res_ar.get("sql_query"))
    print("  Chart Config (AR):", ai_res_ar.get("chart_config"))
    assert ai_res_ar.get("sql_query") is not None
    assert ai_res_ar.get("query_result") is not None

    print("\n ALL BACKEND INTEGRATION TESTS PASSED SUCCESSFULLY! ")

if __name__ == "__main__":
    run_tests()
