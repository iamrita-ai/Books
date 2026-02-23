from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import InlineQueryHandler, CallbackContext
from database import search_files
from utils import format_size
import logging

logger = logging.getLogger(__name__)

def inline_query(update: Update, context):
    query = update.inline_query.query
    if not query:
        return

    results = search_files(query)[:50]  # Max 50 results
    inline_results = []
    for book in results:
        caption = f"📘 {book['original_filename']}\n📦 {format_size(book['file_size'])}"
        inline_results.append(
            InlineQueryResultArticle(
                id=str(book['id']),
                title=book['original_filename'],
                description=f"Size: {format_size(book['file_size'])}",
                input_message_content=InputTextMessageContent(
                    f"📘 <b>{book['original_filename']}</b>\n📦 {format_size(book['file_size'])}",
                    parse_mode='HTML'
                )
            )
        )
    update.inline_query.answer(inline_results, cache_time=5)

inline_handler = InlineQueryHandler(inline_query)
