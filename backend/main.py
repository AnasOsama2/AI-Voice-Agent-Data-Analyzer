import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import (
    BASE_DIR, GROQ_API_KEY, WHISPER_MODEL, LLM_MODEL,
    UPLOADS_DIR, AUDIO_DIR, DATABASES_DIR
)
from backend.database import (
    create_session, list_sessions, get_session, delete_session,
    update_session_title, add_message, ingest_dataset
)
from backend.agent import run_agent_pipeline, transcribe_audio

app = FastAPI(
    title="AI Voice Data Analyzer API",
    description="Full-stack AI Data Analysis via Voice (Whisper-large-v3-turbo) and SQL (Qwen 3.6-27B)",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount audio and uploads static directories
app.mount("/static/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Analysis Session"

class UpdateSessionRequest(BaseModel):
    title: str

class TextQueryRequest(BaseModel):
    prompt: str

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "groq_configured": bool(GROQ_API_KEY),
        "whisper_model": WHISPER_MODEL,
        "llm_model": LLM_MODEL
    }

@app.post("/api/sessions")
async def api_create_session(body: CreateSessionRequest = CreateSessionRequest()):
    session_id = str(uuid.uuid4())
    session = create_session(session_id, body.title or "New Analysis Session")
    return session

@app.get("/api/sessions")
async def api_list_sessions():
    return list_sessions()

@app.get("/api/sessions/{session_id}")
async def api_get_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.patch("/api/sessions/{session_id}")
async def api_update_session(session_id: str, body: UpdateSessionRequest):
    update_session_title(session_id, body.title)
    return {"status": "ok", "session_id": session_id, "title": body.title}

@app.delete("/api/sessions/{session_id}")
async def api_delete_session(session_id: str):
    delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@app.post("/api/sessions/{session_id}/upload")
async def api_upload_dataset(session_id: str, file: UploadFile = File(...)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Only .csv, .xlsx, and .xls are supported."
        )

    # Save uploaded file
    file_id = str(uuid.uuid4())
    saved_filename = f"{session_id}_{file_id}_{file.filename}"
    file_path = UPLOADS_DIR / saved_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        dataset_meta = ingest_dataset(session_id, file_path, file.filename)
        # Update session title if default
        if session["title"] == "New Analysis Session":
            stem_name = Path(file.filename).stem.replace("_", " ").replace("-", " ").title()
            update_session_title(session_id, f"Analysis: {stem_name}")
            
        return dataset_meta
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to parse and ingest file: {str(e)}")

@app.post("/api/sessions/{session_id}/query")
async def api_query_session(
    session_id: str,
    prompt: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None)
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_path = None
    audio_url = None
    if audio:
        audio_id = str(uuid.uuid4())
        audio_filename = f"{session_id}_{audio_id}_{audio.filename}"
        audio_path = AUDIO_DIR / audio_filename
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        audio_url = f"/static/audio/{audio_filename}"

    try:
        # Retrieve recent chat history for context
        chat_history = session.get("messages", [])
        
        # Run agent
        result = run_agent_pipeline(
            session_id=session_id,
            user_prompt=prompt,
            audio_file_path=audio_path,
            chat_history=chat_history
        )
        
        user_msg_id = str(uuid.uuid4())
        asst_msg_id = str(uuid.uuid4())
        
        user_content = result.get("prompt") or prompt or "Voice Query"
        
        # Save User Message
        user_msg = add_message(
            session_id=session_id,
            message_id=user_msg_id,
            role="user",
            content=user_content,
            audio_url=audio_url,
            transcript=result.get("transcript")
        )
        
        # Save Assistant Message
        asst_msg = add_message(
            session_id=session_id,
            message_id=asst_msg_id,
            role="assistant",
            content=result.get("answer") or "",
            sql_query=result.get("sql_query"),
            query_result=result.get("query_result"),
            chart_config=result.get("chart_config"),
            reasoning=result.get("reasoning")
        )
        
        return {
            "user_message": user_msg,
            "assistant_message": asst_msg,
            "execution_time_ms": result.get("execution_time_ms")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe")
async def api_transcribe_audio(audio: UploadFile = File(...)):
    """Standalone audio transcription for microphone test or voice preview."""
    audio_id = str(uuid.uuid4())
    audio_filename = f"test_{audio_id}_{audio.filename}"
    audio_path = AUDIO_DIR / audio_filename
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
        
    try:
        res = transcribe_audio(audio_path)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if audio_path.exists():
            try:
                audio_path.unlink()
            except Exception:
                pass

@app.post("/api/create-demo-dataset")
async def api_create_demo_dataset():
    """Generates a demo e-commerce sales dataset with bilingual columns for instant testing."""
    session_id = str(uuid.uuid4())
    session = create_session(session_id, "Sample Sales & Revenue Dataset")
    
    # Create sample CSV
    demo_file = UPLOADS_DIR / f"{session_id}_sales_demo.csv"
    demo_data = """Order_ID,Customer_Name,Region,المنطقة,Product_Category,المنتج,Units_Sold,Unit_Price,Total_Revenue,Order_Date,Status
1001,Ahmed Al-Mansoor,Riyadh,الرياض,Electronics,شاشات ذكية,12,450.00,5400.00,2026-01-10,Completed
1002,Sara Al-Otaibi,Jeddah,جدة,Accessories,سماعات لاسلكية,25,80.00,2000.00,2026-01-12,Completed
1003,Omar Khalid,Dammam,الدمام,Computers,أجهزة لابتوب,8,1200.00,9600.00,2026-01-15,Completed
1004,Fatima Hassan,Riyadh,الرياض,Home Appliances,صانعة قهوة,15,150.00,2250.00,2026-01-18,Shipped
1005,Zaid Al-Harbi,Medina,المدينة,Electronics,ساعات ذكية,30,110.00,3300.00,2026-01-20,Completed
1006,Noura Al-Dosari,Khobar,الخبر,Computers,شاشات كمبيوتر,14,320.00,4480.00,2026-01-22,Completed
1007,Youssef Adel,Riyadh,الرياض,Accessories,كيبورد ميكانيكي,40,65.00,2600.00,2026-01-25,Cancelled
1008,Maha Al-Shehri,Abha,أبها,Home Appliances,مكنسة روبوت,6,600.00,3600.00,2026-01-28,Completed
1009,Tariq Nasser,Jeddah,جدة,Electronics,شاشات ذكية,18,450.00,8100.00,2026-02-02,Completed
1010,Layla Al-Amri,Tabuk,تبوك,Computers,أجهزة لابتوب,5,1200.00,6000.00,2026-02-05,Completed
1011,Hassan Al-Ghamdi,Dammam,الدمام,Accessories,سماعات رأس,35,95.00,3325.00,2026-02-08,Completed
1012,Reem Al-Qahtani,Riyadh,الرياض,Electronics,كاميرات مراقبة,20,180.00,3600.00,2026-02-10,Completed
"""
    with open(demo_file, "w", encoding="utf-8") as f:
        f.write(demo_data)
        
    ingest_dataset(session_id, demo_file, "sales_demo.csv")
    return get_session(session_id)

# Mount frontend production build if available
DIST_DIR = BASE_DIR / "frontend" / "dist"
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="spa-assets")

@app.get("/{full_path:path}")
async def serve_spa_frontend(full_path: str):
    if full_path.startswith("api") or full_path.startswith("static"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "AI Voice Data Analyzer API is running. Frontend build not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
