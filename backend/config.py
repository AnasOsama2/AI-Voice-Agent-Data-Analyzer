import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or current dir
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Groq API Configuration
# Support both GROQ_API_KEY and groq_key
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("groq_key") or ""
if not GROQ_API_KEY:
    # Look for any case variations
    for key, val in os.environ.items():
        if "groq" in key.lower() and "key" in key.lower():
            GROQ_API_KEY = val
            break

# Model defaults
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3.6-27b")

# Storage paths
STORAGE_DIR = BASE_DIR / "backend" / "storage"
DATABASES_DIR = STORAGE_DIR / "databases"
UPLOADS_DIR = STORAGE_DIR / "uploads"
AUDIO_DIR = STORAGE_DIR / "audio"

for d in [STORAGE_DIR, DATABASES_DIR, UPLOADS_DIR, AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# System database path for metadata, chat history, and session tracking
SYSTEM_DB_PATH = STORAGE_DIR / "system.sqlite3"
