from telegram.ext import MessageHandler, Filters
from telegram import Update, ParseMode
from config import SOURCE_CHANNEL, MAX_FILE_SIZE, LOG_CHANNEL
from database import add_file
from utils import log_to_channel, format_size
import logging

logger = logging.getLogger(__name__)

def channel_post_handler(update: Update, context):
    if not update.channel_post or update.channel_post.chat.id != SOURCE_CHANNEL:
        return

    doc = update.channel_post.document
    if not doc:
        return

    if doc.file_size > MAX_FILE_SIZE:
        log_to_channel(context.bot,
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
        context.bot.send_message(
            chat_id=SOURCE_CHANNEL,
            text=f"✅ **PDF Saved Successfully!**\n📄 `{doc.file_name}`\n📦 Size: {format_size(doc.file_size)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=update.channel_post.message_id
        )
        log_to_channel(context.bot,
            f"📚 New PDF added: {doc.file_name}\nSize: {format_size(doc.file_size)}")
    else:
        context.bot.send_message(
            chat_id=SOURCE_CHANNEL,
            text="⚠️ This PDF is already in the database.",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=update.channel_post.message_id
        )

channel_handler = MessageHandler(
    Filters.chat(chat_id=SOURCE_CHANNEL) & Filters.document,
    channel_post_handler
)
