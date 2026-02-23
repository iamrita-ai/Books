import re
import random
import requests
import time
from datetime import datetime
import psutil
from config import FORCE_SUB_CHANNEL, LOG_CHANNEL, BOT_TOKEN, OWNER_ID, OWNER_USERNAME, REQUEST_GROUP, MESSAGE_RETRY_DELAY
import logging
from telegram.error import RetryAfter, TimedOut

logger = logging.getLogger(__name__)

def normalize_name(name: str) -> str:
    """Normalize book name for search: lowercase, remove special chars, extra spaces."""
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def random_reaction() -> str:
    """Return a random emoji for reactions."""
    emojis = [
        "👍", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🎉",
        "🤩", "🙏", "👌", "🕊️", "🤝", "😍", "😘", "💯", "💪", "🍓"
    ]
    return random.choice(emojis)

def send_reaction(chat_id: int, message_id: int, emoji: str, is_big: bool = False, max_retries: int = 2) -> bool:
    """Send reaction via direct API call with flood and invalid emoji handling."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": emoji}]
    }
    if is_big:
        data["is_big"] = True

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=5)
            result = response.json()
            if result.get("ok"):
                return True

            desc = result.get("description", "").lower()
            if "retry after" in desc:
                wait = int(result.get("parameters", {}).get("retry_after", MESSAGE_RETRY_DELAY))
                logger.warning(f"Reaction flood, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            elif "reaction_invalid" in desc:
                logger.warning(f"Invalid reaction emoji: {emoji}")
                return False
            else:
                logger.error(f"Reaction failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Reaction error: {e}")
            if attempt < max_retries - 1:
                time.sleep(MESSAGE_RETRY_DELAY)
            else:
                return False
    return False

def safe_send_message(bot, chat_id, text, parse_mode=None, reply_markup=None, reply_to_message_id=None, max_retries=3):
    """Send a message with automatic retry on flood/timeout."""
    for attempt in range(max_retries):
        try:
            return bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id
            )
        except RetryAfter as e:
            wait = e.retry_after
            logger.warning(f"Flood control: waiting {wait}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
        except TimedOut:
            logger.warning(f"Timeout, retrying in {MESSAGE_RETRY_DELAY}s")
            time.sleep(MESSAGE_RETRY_DELAY)
        except Exception as e:
            logger.error(f"Send message error: {e}")
            if attempt < max_retries - 1:
                time.sleep(MESSAGE_RETRY_DELAY)
            else:
                raise
    raise Exception("Max retries exceeded while sending message")

def safe_reply_text(message, text, parse_mode=None, reply_markup=None, max_retries=3):
    """Helper to reply to a message with retry."""
    return safe_send_message(
        message.bot,
        message.chat_id,
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        reply_to_message_id=message.message_id,
        max_retries=max_retries
    )

def check_subscription(user_id, bot):
    """Check if user is subscribed to the force sub channel."""
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False

def log_to_channel(bot, text: str):
    """Send log message to the configured log channel."""
    if not LOG_CHANNEL:
        return
    try:
        bot.send_message(chat_id=LOG_CHANNEL, text=text)
    except Exception as e:
        logger.error(f"Log to channel failed: {e}")

def get_uptime(start_time: datetime) -> str:
    """Return formatted uptime string."""
    delta = datetime.now() - start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def get_memory_usage():
    """Return memory usage in MB."""
    try:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except:
        return None

def get_disk_usage():
    """Return disk usage of current directory in MB."""
    try:
        usage = psutil.disk_usage('.')
        return usage.used / (1024 * 1024)
    except:
        return None

def build_start_keyboard():
    """Build the inline keyboard for /start message."""
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

    if REQUEST_GROUP:
        if REQUEST_GROUP.startswith('@'):
            buttons.append(InlineKeyboardButton("📝 Request Group", url=f"https://t.me/{REQUEST_GROUP[1:]}"))
        else:
            buttons.append(InlineKeyboardButton("📝 Request Group", url=REQUEST_GROUP))

    buttons.append(InlineKeyboardButton("ℹ️ Info", callback_data="info"))
    return [buttons]  # list of rows

def build_info_keyboard():
    """Build the info row for search results (owner, channel, info)."""
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
    return [buttons]  # list of rows
