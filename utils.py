import re
import random
from datetime import datetime
import psutil
from config import FORCE_SUB_CHANNEL, LOG_CHANNEL

def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def random_reaction() -> str:
    """Return a random emoji from Telegram's supported reaction set."""
    emojis = [
        "👍", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🎉",
        "🤩", "🙏", "👌", "🕊️", "🤝", "😍", "😘", "💯", "💪", "🍓"
    ]
    return random.choice(emojis)

async def check_subscription(user_id, bot) -> bool:
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def log_to_channel(bot, text: str):
    try:
        await bot.send_message(chat_id=LOG_CHANNEL, text=text)
    except Exception:
        pass

def get_uptime(start_time: datetime) -> str:
    delta = datetime.now() - start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def get_memory_usage():
    try:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except:
        return None

def get_disk_usage():
    try:
        usage = psutil.disk_usage('.')
        return usage.used / (1024 * 1024)
    except:
        return None
