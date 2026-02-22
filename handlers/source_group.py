from telegram.ext import MessageHandler, Filters
from telegram import Update, ParseMode
from config import SOURCE_CHANNELS, MAX_FILE_SIZE, LOG_CHANNEL
from database import add_file
from utils import log_to_channel, format_size
import logging
import traceback

logger = logging.getLogger(__name__)

def source_group_handler(update: Update, context):
    """Handle documents from any source group."""
    try:
        chat_id = update.effective_chat.id
        message = update.message
        logger.info(f"⚡ source_group_handler CALLED for chat {chat_id}")

        # Verify it's one of the source groups
        if chat_id not in SOURCE_CHANNELS:
            logger.warning(f"Ignoring message from chat {chat_id} (not in source list)")
            return

        # Must be a document
        if not message or not message.document:
            logger.info("No document in message, ignoring")
            return

        doc = message.document
        logger.info(f"📄 Document received: {doc.file_name} ({doc.file_size} bytes)")
        logger.info(f"📄 File ID: {doc.file_id}")

        # Size check
        if doc.file_size > MAX_FILE_SIZE:
            logger.warning(f"File too large: {format_size(doc.file_size)} > {format_size(MAX_FILE_SIZE)}")
            log_to_channel(context.bot, f"🚫 Ignored large file: {doc.file_name} ({format_size(doc.file_size)})")
            return

        # Save to database
        added = add_file(
            file_id=doc.file_id,
            file_unique_id=doc.file_unique_id,
            original_filename=doc.file_name,
            file_size=doc.file_size,
            message_id=message.message_id,
            channel_id=chat_id
        )

        if added:
            logger.info(f"✅ File added to database: {doc.file_name}")
            message.reply_text(
                f"✅ **PDF Saved Successfully!**\n📄 `{doc.file_name}`\n📦 Size: {format_size(doc.file_size)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=message.message_id
            )
            log_to_channel(context.bot, f"📚 New PDF added: {doc.file_name}\nSize: {format_size(doc.file_size)}")
        else:
            logger.info(f"⚠️ Duplicate file: {doc.file_name}")
            message.reply_text(
                "⚠️ This PDF is already in the database.",
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=message.message_id
            )

    except Exception as e:
        logger.error(f"❌ Error in source_group_handler: {e}\n{traceback.format_exc()}")
        try:
            context.bot.send_message(
                chat_id=LOG_CHANNEL,
                text=f"❌ Error processing document: {e}"
            )
        except:
            pass

# ✅ Simple handler: accepts all documents, but filters inside the function
source_group_handler_obj = MessageHandler(
    Filters.document,
    source_group_handler
)
