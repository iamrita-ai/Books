from telegram.ext import filters, MessageHandler, Filters
from telegram import Update
from config import SOURCE_CHANNEL, MAX_FILE_SIZE, LOG_CHANNEL
from database import add_file
from utils import log_to_channel, format_size
import logging

logger = logging.getLogger(__name__)

async def channel_post_handler(update: Update, context):
    if not update.channel_post or update.channel_post.chat.id != SOURCE_CHANNEL:
        return

    doc = update.channel_post.document
    if not doc:
        return

    if doc.file_size > MAX_FILE_SIZE:
        await log_to_channel(context.bot,
            f"🚫 Ignored large file: {doc.file_name} ({format_size(doc.file_size)})")
        return

    added = add_file(
        file_id=doc.file_id,
        file_unique_id=doc.file_unique_id,
        original_filename=doc.file_name,
        file_size=doc.file_size,
        message_id=update.channel_post.message_id,
        channel_id=SOURCE_CHANNEL
    )
    if added:
        await log_to_channel(context.bot,
            f"📚 New PDF added: {doc.file_name}\nSize: {format_size(doc.file_size)}")

# ✅ FIX: Use Filters.document (with capital F) and filters.Chat with positional args
channel_handler = MessageHandler(
    filters.Chat(SOURCE_CHANNEL, 'channel') & Filters.document,
    channel_post_handler
)
