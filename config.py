import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
OWNER_ID = int(os.getenv("OWNER_ID"))
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL")   # e.g., "@myChannel" or channel ID as string
SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))    # numeric channel ID
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))          # numeric channel ID for logs

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
RESULTS_PER_PAGE = 10

DATABASE = "bot_data.db"

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://localhost")
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}/webhook"
