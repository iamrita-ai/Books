import re
import random
from config import LOG_CHANNEL

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

def random_reaction():
    emojis = ["👍","❤️","🔥","🥰","👏","😁","🤔","🤯","😱","🎉","🤩","🙏","👌","🕊️","🤝","😍","😘","💯","💪","🍓"]
    return random.choice(emojis)

def check_subscription(user_id, bot):
    from config import FORCE_SUB_CHANNEL
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def log_to_channel(bot, text):
    try:
        bot.send_message(chat_id=LOG_CHANNEL, text=text)
    except:
        pass
