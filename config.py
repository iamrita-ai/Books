import os
from dotenv import load_dotenv

load_dotenv()  # For local development; on Render env vars are set via dashboard

# Bot credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
OWNER_ID = int(os.getenv("OWNER_ID"))
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Channels
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL")  # e.g., "@myChannel" or channel ID (as string)
SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))   # numeric channel ID
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))         # numeric channel ID for logs

# Limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
RESULTS_PER_PAGE = 10

# Database
DATABASE = "bot_data.db"

# Webhook URL (Render provides this env var automatically)
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://localhost")
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}/webhook"
