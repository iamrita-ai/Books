from telegram.ext import MessageHandler, Filters
from telegram import Update, ParseMode
from config import SOURCE_CHANNEL, MAX_FILE_SIZE, LOG_CHANNEL
from database import add_file
from utils import log_to_channel, format_size
import logging

logger = logging.getLogger(__name__)

def source_group_handler(update: Update, context):
    """Handle documents from the source group (where PDFs are uploaded)."""
    # Log for debugging
    logger.info(f"Message received in chat {update.effective_chat.id}")

    # Check if it's our source group
    if update.effective_chat.id != SOURCE_CHANNEL:
        logger.warning(f"Ignoring message from chat {update.effective_chat.id}")
        return

    # Check if it has a document
    if not update.message or not update.message.document:
        logger.info("No document, ignoring")
        return

    doc = update.message.document
    logger.info(f"Document received: {doc.file_name} ({doc.file_size} bytes)")

    if doc.file_size > MAX_FILE_SIZE:
        logger.warning(f"File too large: {format_size(doc.file_size)} > {format_size(MAX_FILE_SIZE)}")
        log_to_channel(context.bot,
            f"🚫 Ignored large file: {doc.file_name} ({format_size(doc.file_size)})")
        return

    added = add_file(
        file_id=doc.file_id,
        file_unique_id=doc.file_unique_id,
        original_filename=doc.file_name,
        file_size=doc.file_size,
        message_id=update.message.message_id,
        channel_id=SOURCE_CHANNEL
    )
    if added:
        logger.info(f"File added to database: {doc.file_name}")
        # Reply in the group
        update.message.reply_text(
            f"✅ **PDF Saved Successfully!**\n📄 `{doc.file_name}`\n📦 Size: {format_size(doc.file_size)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=update.message.message_id
        )
        log_to_channel(context.bot,
            f"📚 New PDF added: {doc.file_name}\nSize: {format_size(doc.file_size)}")
    else:
        logger.info(f"Duplicate file: {doc.file_name}")
        update.message.reply_text(
            "⚠️ This PDF is already in the database.",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=update.message.message_id
        )

# Handler for source group
source_group_handler_obj = MessageHandler(
    Filters.chat(chat_id=SOURCE_CHANNEL) & Filters.document,
    source_group_handler
)
