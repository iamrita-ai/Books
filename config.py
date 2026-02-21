import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", "📚 PDF Library Bot")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@Xioqui_xin")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")

FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL")  # e.g., @serenaunzip
SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL", 0))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", 0))

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
RESULTS_PER_PAGE = 10

DATABASE = "bot_data.db"
REQUEST_GROUP = os.getenv("REQUEST_GROUP")  # e.g., private group link
