import re
import random
import requests
import time
from datetime import datetime
import psutil
from config import (
    FORCE_SUB_CHANNEL, LOG_CHANNEL, BOT_TOKEN, OWNER_ID,
    OWNER_USERNAME, REQUEST_GROUP, MESSAGE_RETRY_DELAY
)
import logging
from telegram.error import RetryAfter, TimedOut

logger = logging.getLogger(__name__)

# ==================== FANCY FONT & DECORATION FUNCTIONS ====================

def fancy_bold(text):
    """Convert text to unicode bold (mathematical bold)."""
    bold_map = {
        'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠',
        'h': '𝐡', 'i': '𝐢', 'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧',
        'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭', 'u': '𝐮',
        'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳',
        'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆',
        'H': '𝐇', 'I': '𝐈', 'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍',
        'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓', 'U': '𝐔',
        'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
        '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔',
        '7': '𝟕', '8': '𝟖', '9': '𝟗'
    }
    return ''.join(bold_map.get(c, c) for c in text)

def fancy_italic(text):
    """Convert text to unicode italic (mathematical italic)."""
    italic_map = {
        'a': '𝑎', 'b': '𝑏', 'c': '𝑐', 'd': '𝑑', 'e': '𝑒', 'f': '𝑓', 'g': '𝑔',
        'h': 'ℎ', 'i': '𝑖', 'j': '𝑗', 'k': '𝑘', 'l': '𝑙', 'm': '𝑚', 'n': '𝑛',
        'o': '𝑜', 'p': '𝑝', 'q': '𝑞', 'r': '𝑟', 's': '𝑠', 't': '𝑡', 'u': '𝑢',
        'v': '𝑣', 'w': '𝑤', 'x': '𝑥', 'y': '𝑦', 'z': '𝑧',
        'A': '𝐴', 'B': '𝐵', 'C': '𝐶', 'D': '𝐷', 'E': '𝐸', 'F': '𝐹', 'G': '𝐺',
        'H': '𝐻', 'I': '𝐼', 'J': '𝐽', 'K': '𝐾', 'L': '𝐿', 'M': '𝑀', 'N': '𝑁',
        'O': '𝑂', 'P': '𝑃', 'Q': '𝑄', 'R': '𝑅', 'S': '𝑆', 'T': '𝑇', 'U': '𝑈',
        'V': '𝑉', 'W': '𝑊', 'X': '𝑋', 'Y': '𝑌', 'Z': '𝑍'
    }
    return ''.join(italic_map.get(c, c) for c in text)

def decorative_header(title=""):
    """Return a decorative header with title."""
    header = "𓍯𓂃♡ִֶָ  ⋆ ˚｡⋆୨୧˚  " + title + "  ˚୨୧⋆｡˚ ⋆  𓍯𓂃♡ִֶָ"
    return header

def decorative_footer():
    """Return a decorative footer."""
    return "┗━━━━━༻❁༺━━━━━┛  𓆩♡𓆪  ＊*•̩̩͙✩•̩̩͙*˚"

def section_divider():
    """Return a decorative section divider."""
    return "═══════🪼⋆.ೃ࿔*:･  િ⁀➴  ☕︎  ═══════"

def star_line():
    """Return a line of stars."""
    return "⋆｡°✩ ⋆｡°✩ ⋆｡°✩ ⋆｡°✩"

def cute_border():
    """Return a cute border line."""
    return "·͙*̩̩͙˚̩̥̩̥*̩̩̥͙　✩　*̩̩̥͙˚̩̥̩̥*̩̩͙‧͙"

def romantic_heart():
    """Return a romantic heart decoration."""
    return "𓆩♡𓆪"

# ==================== EXISTING FUNCTIONS ====================

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

def send_reaction(chat_id: int, message_id: int, emoji: str, is_big: bool = False, max_retries=2):
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
            elif "retry after" in result.get("description", "").lower():
                wait = int(result.get("parameters", {}).get("retry_after", MESSAGE_RETRY_DELAY))
                logger.warning(f"Reaction flood, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            elif "REACTION_INVALID" in result.get("description", ""):
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
    raise Exception("Max retries exceeded")

def safe_reply_text(message, text, parse_mode=None, reply_markup=None, max_retries=3):
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
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False

def log_to_channel(bot, text: str):
    if not LOG_CHANNEL:
        return
    try:
        bot.send_message(chat_id=LOG_CHANNEL, text=text)
    except Exception as e:
        logger.error(f"Log to channel failed: {e}")

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
    return [buttons]

def build_info_keyboard():
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
    return [buttons]

def format_book_caption(book):
    """Generate a beautiful caption for a book with all metadata."""
    parts = []
    if book.get('author'):
        parts.append(f"✍️ <b>Author:</b> {book['author']}")
    if book.get('category'):
        parts.append(f"📚 <b>Category:</b> {book['category']}")
    if book.get('language'):
        lang = "English" if book['language'] == 'en' else "Hindi" if book['language'] == 'hi' else book['language']
        parts.append(f"🌐 <b>Language:</b> {lang}")
    if book.get('year'):
        parts.append(f"📅 <b>Year:</b> {book['year']}")
    if book.get('pages'):
        parts.append(f"📄 <b>Pages:</b> {book['pages']}")
    if book.get('file_size'):
        parts.append(f"📦 <b>Size:</b> {format_size(book['file_size'])}")
    parts.append(f"🆔 <b>Book ID:</b> <code>{book['id']}</code>")
    return "\n".join(parts)
