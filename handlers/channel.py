from telegram.ext import MessageHandler, Filters
from telegram import Update, ParseMode
from config import SOURCE_CHANNEL, MAX_FILE_SIZE, LOG_CHANNEL
from database import add_file
from utils import log_to_channel, format_size
import logging

logger = logging.getLogger(__name__)

def document_handler(update: Update, context):
    """Handle documents from the specified source chat (channel or group)."""
    # Determine if it's a channel post or a group message
    if update.channel_post:
        chat_id = update.channel_post.chat.id
        message = update.channel_post
        logger.info(f"Channel post received from chat {chat_id}")
    elif update.message:
        chat_id = update.message.chat.id
        message = update.message
        logger.info(f"Group message received from chat {chat_id}")
    else:
        return

    # Check if it's the correct source chat
    if chat_id != SOURCE_CHANNEL:
        logger.info(f"Ignoring message from chat {chat_id} (expected {SOURCE_CHANNEL})")
        return

    doc = message.document
    if not doc:
        logger.info("No document in message")
        return

    logger.info(f"Document received: {doc.file_name}, size: {doc.file_size}")

    if doc.file_size > MAX_FILE_SIZE:
        logger.warning(f"File too large: {doc.file_size} > {MAX_FILE_SIZE}")
        log_to_channel(context.bot,
            f"🚫 Ignored large file: {doc.file_name} ({format_size(doc.file_size)})")
        return

    added = add_file(
        file_id=doc.file_id,
        file_unique_id=doc.file_unique_id,
        original_filename=doc.file_name,
        file_size=doc.file_size,
        message_id=message.message_id,
        channel_id=SOURCE_CHANNEL
    )

    if added:
        # Reply in the same chat
        context.bot.send_message(
            chat_id=SOURCE_CHANNEL,
            text=f"✅ **PDF Saved Successfully!**\n📄 `{doc.file_name}`\n📦 Size: {format_size(doc.file_size)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.message_id
        )
        log_to_channel(context.bot,
            f"📚 New PDF added: {doc.file_name}\nSize: {format_size(doc.file_size)}")
        logger.info(f"PDF saved: {doc.file_name}")
    else:
        # Duplicate
        context.bot.send_message(
            chat_id=SOURCE_CHANNEL,
            text="⚠️ This PDF is already in the database.",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.message_id
        )
        logger.info(f"Duplicate PDF ignored: {doc.file_name}")

# Handler for documents in the specific source chat (works for both channel and group)
channel_handler = MessageHandler(
    Filters.chat(chat_id=SOURCE_CHANNEL) & Filters.document,
    document_handler
)
