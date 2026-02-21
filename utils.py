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
    emojis = [
        "👍", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🎉",
        "🤩", "🙏", "👌", "🕊️", "🤝", "😍", "😘", "💯", "💪", "🍓"
    ]
    return random.choice(emojis)

def check_subscription(user_id, bot):
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def log_to_channel(bot, text: str):
    try:
        bot.send_message(chat_id=LOG_CHANNEL, text=text)
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

def build_info_keyboard():
    """Build the info row with owner contact and channel."""
    from telegram import InlineKeyboardButton
    from config import OWNER_ID, OWNER_USERNAME, FORCE_SUB_CHANNEL
    buttons = []
    
    # Owner button
    if OWNER_USERNAME:
        owner_display = OWNER_USERNAME if OWNER_USERNAME.startswith('@') else f"@{OWNER_USERNAME}"
        buttons.append(InlineKeyboardButton("👤 Owner", url=f"https://t.me/{owner_display[1:]}"))
    elif OWNER_ID:
        buttons.append(InlineKeyboardButton("👤 Owner", url=f"tg://user?id={OWNER_ID}"))
    
    # Channel button
    if FORCE_SUB_CHANNEL:
        channel_display = FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL.startswith('@') else f"@{FORCE_SUB_CHANNEL}"
        buttons.append(InlineKeyboardButton("📢 Channel", url=f"https://t.me/{channel_display[1:]}"))
    
    buttons.append(InlineKeyboardButton("ℹ️ Info", callback_data="info"))
    return buttons
