from telegram.ext import MessageHandler, Filters
from telegram import Update, ParseMode
from config import SOURCE_CHANNEL, MAX_FILE_SIZE, LOG_CHANNEL
from database import add_file
from utils import log_to_channel, format_size
import logging

logger = logging.getLogger(__name__)

def channel_post_handler(update: Update, context):
    # Log every channel post for debugging
    logger.info(f"Received channel post: chat_id={update.channel_post.chat.id}, message_id={update.channel_post.message_id}")
    
    # Check if it's from our source channel
    if not update.channel_post or update.channel_post.chat.id != SOURCE_CHANNEL:
        logger.warning(f"Ignored channel post from {update.channel_post.chat.id if update.channel_post else 'None'}, expected {SOURCE_CHANNEL}")
        return

    doc = update.channel_post.document
    if not doc:
        logger.info("Channel post is not a document")
        return

    # Check file size
    if doc.file_size > MAX_FILE_SIZE:
        log_to_channel(context.bot,
            f"🚫 Ignored large file: {doc.file_name} ({format_size(doc.file_size)})")
        logger.info(f"Ignored large file: {doc.file_name}")
        return

    # Try to add to database
    added = add_file(
        file_id=doc.file_id,
        file_unique_id=doc.file_unique_id,
        original_filename=doc.file_name,
        file_size=doc.file_size,
        message_id=update.channel_post.message_id,
        channel_id=SOURCE_CHANNEL
    )
    
    if added:
        # Reply in channel
        context.bot.send_message(
            chat_id=SOURCE_CHANNEL,
            text=f"✅ **PDF Saved Successfully!**\n📄 `{doc.file_name}`\n📦 Size: {format_size(doc.file_size)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=update.channel_post.message_id
        )
        log_to_channel(context.bot,
            f"📚 New PDF added: {doc.file_name}\nSize: {format_size(doc.file_size)}")
        logger.info(f"Added new PDF: {doc.file_name}")
    else:
        # Duplicate
        context.bot.send_message(
            chat_id=SOURCE_CHANNEL,
            text="⚠️ This PDF is already in the database.",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=update.channel_post.message_id
        )
        logger.info(f"Duplicate PDF: {doc.file_name}")

# Use Filters.chat with correct syntax
channel_handler = MessageHandler(
    Filters.chat(chat_id=SOURCE_CHANNEL) & Filters.document,
    channel_post_handler
)
