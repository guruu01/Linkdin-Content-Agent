import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "content_agent.db"
CALENDAR_PATH = DATA_DIR / "linkedin_content_calendar.xlsx"

class Settings:
    def __init__(self):
        self.reload()

    def reload(self):
        load_dotenv(ENV_PATH, override=True)
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")

        self.DEFAULT_TOPIC: str = os.getenv("DEFAULT_TOPIC", "AI and product management developments")
        self.WORKFLOW_SCHEDULE_DAY: str = os.getenv("WORKFLOW_SCHEDULE_DAY", "mon")
        self.WORKFLOW_SCHEDULE_TIME: str = os.getenv("WORKFLOW_SCHEDULE_TIME", "09:00")
        self.AUTO_PUBLISH_APPROVED: bool = os.getenv("AUTO_PUBLISH_APPROVED", "false").lower() in ("true", "1", "yes")

        self.TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.RECIPIENT_WHATSAPP_NUMBER: str = os.getenv("RECIPIENT_WHATSAPP_NUMBER", "")

        self.NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
        self.NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")

        self.GOOGLE_SERVICE_ACCOUNT_PATH: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "")
        self.GOOGLE_SHEETS_SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
        self.GOOGLE_SHEETS_WEBHOOK_URL: str = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")

        self.LINKEDIN_ACCESS_TOKEN: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self.LINKEDIN_AUTHOR_URN: str = os.getenv("LINKEDIN_AUTHOR_URN", "")

        self.APP_HOST: str = os.getenv("HOST", os.getenv("APP_HOST", "0.0.0.0"))
        self.APP_PORT: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))

settings = Settings()

def get_env_dict():
    """Reads current values from .env"""
    settings.reload()
    return {
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "DEFAULT_LLM_PROVIDER": settings.DEFAULT_LLM_PROVIDER,
        "DEFAULT_TOPIC": settings.DEFAULT_TOPIC,
        "WORKFLOW_SCHEDULE_DAY": settings.WORKFLOW_SCHEDULE_DAY,
        "WORKFLOW_SCHEDULE_TIME": settings.WORKFLOW_SCHEDULE_TIME,
        "TWILIO_ACCOUNT_SID": settings.TWILIO_ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
        "TWILIO_WHATSAPP_FROM": settings.TWILIO_WHATSAPP_FROM,
        "RECIPIENT_WHATSAPP_NUMBER": settings.RECIPIENT_WHATSAPP_NUMBER,
        "NOTION_API_KEY": settings.NOTION_API_KEY,
        "NOTION_DATABASE_ID": settings.NOTION_DATABASE_ID,
        "GOOGLE_SERVICE_ACCOUNT_PATH": settings.GOOGLE_SERVICE_ACCOUNT_PATH,
        "GOOGLE_SHEETS_SPREADSHEET_ID": settings.GOOGLE_SHEETS_SPREADSHEET_ID,
        "GOOGLE_SHEETS_WEBHOOK_URL": settings.GOOGLE_SHEETS_WEBHOOK_URL,
        "LINKEDIN_ACCESS_TOKEN": settings.LINKEDIN_ACCESS_TOKEN,
        "LINKEDIN_AUTHOR_URN": settings.LINKEDIN_AUTHOR_URN,
        "AUTO_PUBLISH_APPROVED": "true" if settings.AUTO_PUBLISH_APPROVED else "false"
    }

def update_env_file(new_values: dict):
    """Updates key-value pairs in .env without wiping other comments"""
    lines = []
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    existing_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            existing_keys.add(k)
            if k in new_values:
                val = str(new_values[k]).strip()
                if " " in val and not (val.startswith('"') and val.endswith('"')):
                    val = f'"{val}"'
                new_lines.append(f"{k}={val}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k, v in new_values.items():
        if k not in existing_keys:
            val = str(v).strip()
            if " " in val and not (val.startswith('"') and val.endswith('"')):
                val = f'"{val}"'
            new_lines.append(f"{k}={val}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    settings.reload()
