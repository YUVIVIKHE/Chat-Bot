import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# API Settings
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "cara_compliance_bot_secret_key_2024")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Database Settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cara_bot.db")

# ChromaDB Settings
CHROMA_PERSIST_DIRECTORY = "chroma_db"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Bot Modules
BOT_MODULES = {
    "1": {"name": "ISO Bot", "description": "Automates ISO 27001 FAQs, control help, and evidence collection."},
    "2": {"name": "RiskBot", "description": "Conversational risk assessment wizard."},
    "3": {"name": "Compliance Coach", "description": "Micro-training, reminders, and policy query support."},
    "4": {"name": "AuditBuddy", "description": "Helps orgs get ready for audits by simulating Q&A or fetching documents."},
    "5": {"name": "Policy Navigator", "description": "Helps users find and understand organizational policies."},
    "6": {"name": "Security Advisor", "description": "Provides security best practices and guidance."}
} 