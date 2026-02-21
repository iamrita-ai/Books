import re
import random
import requests
import time
from datetime import datetime
import psutil
from config import FORCE_SUB_CHANNEL, LOG_CHANNEL, BOT_TOKEN, OWNER_ID, OWNER_USERNAME, REQUEST_GROUP

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

def send_reaction(chat_id: int, message_id: int, emoji: str, is_big: bool = False):
    """Send reaction using direct API call."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": emoji}]
    }
    if is_big:
        data["is_big"] = True
    try:
        response = requests.post(url, json=data, timeout=5)
        return response.json().get("ok", False)
    except Exception as e:
        print(f"Reaction error: {e}")
        return False

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

def build_start_keyboard():
    """Build the inline keyboard for /start message."""
    from telegram import InlineKeyboardButton
    buttons = []
    
    # Owner button
    if OWNER_USERNAME:
        owner_display = OWNER_USERNAME if OWNER_USERNAME.startswith('@') else f"@{OWNER_USERNAME}"
        buttons.append(InlineKeyboardButton("👤 Owner", url=f"https://t.me/{owner_display[1:]}"))
    elif OWNER_ID:
        buttons.append(InlineKeyboardButton("👤 Owner", url=f"tg://user?id={OWNER_ID}"))
    
    # Force sub channel button
    if FORCE_SUB_CHANNEL:
        channel_display = FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL.startswith('@') else f"@{FORCE_SUB_CHANNEL}"
        buttons.append(InlineKeyboardButton("📢 Channel", url=f"https://t.me/{channel_display[1:]}"))
    
    # Request group button
    if REQUEST_GROUP:
        # If it's a username, convert to link, else assume it's a full invite link
        if REQUEST_GROUP.startswith('@'):
            buttons.append(InlineKeyboardButton("📝 Request Group", url=f"https://t.me/{REQUEST_GROUP[1:]}"))
        else:
            buttons.append(InlineKeyboardButton("📝 Request Group", url=REQUEST_GROUP))
    
    # Info button (already handled in callbacks)
    buttons.append(InlineKeyboardButton("ℹ️ Info", callback_data="info"))
    
    # Arrange in a single row? We'll put all in one row if space permits, else we can split.
    # For simplicity, we'll put all in one row. Telegram supports up to 8 buttons per row.
    return [buttons]  # This returns a list of rows (single row)

def build_info_keyboard():
    """Build the info row for search results (same as start but without request group maybe)."""
    from telegram import InlineKeyboardButton
    buttons = []
    
    if OWNER_USERNAME:
        owner_display = OWNER_USERNAME if OWNER_USERNAME.startswith('@') else f"@{OWNER_USERNAME}"
        buttons.append(InlineKeyboardButton("👤 Owner", url=f"https://t.me/{owner_display[1:]}"))
    elif OWNER_ID:
        buttons.append(InlineKeyboardButton("👤 Owner", url=f"tg://user?id={OWNER_ID}"))
    
    if FORCE_SUB_CHANNEL:
        channel_display = FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL.startswith('@') else f"@{FORCE_SUB_CHANNEL}"
        buttons.append(InlineKeyboardButton("📢 Channel", url=f"https://t.me/{channel_display[1:]}"))
    
    buttons.append(InlineKeyboardButton("ℹ️ Info", callback_data="info"))
    return [buttons]  # single row
