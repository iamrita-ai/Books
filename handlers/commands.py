from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatAction
from telegram.ext import CommandHandler, Filters, CallbackContext, MessageHandler
from config import OWNER_ID, BOT_NAME, FORCE_SUB_CHANNEL, REQUEST_GROUP, RESULTS_PER_PAGE
from database import (
    get_total_files, get_total_users, get_db_size, is_bot_locked,
    set_bot_locked, get_all_users, update_user, search_files,
    get_top_books, get_random_book, add_feedback, warn_user, is_user_banned,
    bookmark, get_user_bookmarks, vacuum_db, backup_db, get_db
)
from utils import (
    get_uptime, get_memory_usage, get_disk_usage, check_subscription,
    log_to_channel, build_start_keyboard, build_info_keyboard, format_size,
    safe_reply_text, format_book_caption, decorative_header, decorative_footer,
    section_divider, star_line, cute_border, romantic_heart, fancy_bold
)
import datetime
import logging
import time
import random

logger = logging.getLogger(__name__)

BOT_START_TIME = datetime.datetime.now()

# ==================== Helper Functions ====================

def _check_and_send_force_sub(update: Update, context) -> bool:
    user = update.effective_user
    if not user:
        return False
    if not check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        update.message.reply_text(
            f"{romantic_heart()} My love, you haven't joined our channel yet. Please join to unlock my heart!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    return True

def owner_only(func):
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            update.message.reply_text(f"⛔ You're not the one I belong to, darling. Only my owner can do that.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def send_results_page(update: Update, context: CallbackContext, page):
    """Shared function to display search results with pagination."""
    from utils import build_info_keyboard, format_size
    results = context.user_data.get('search_results', [])
    if not results:
        update.message.reply_text(f"{romantic_heart()} No results found, my dear. Try another name?")
        return

    total = len(results)
    start = page * RESULTS_PER_PAGE
    end = min(start + RESULTS_PER_PAGE, total)
    page_results = results[start:end]

    keyboard = []
    for res in page_results:
        btn_text = f"📘 {res['original_filename']} ({format_size(res['file_size'])})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_{res['id']}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page_{page-1}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    info_buttons = build_info_keyboard()
    if info_buttons:
        keyboard.extend(info_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"{decorative_header('ꜰᴏᴜɴᴅ ꜱᴏᴍᴇᴛʜɪɴɢ')}\n\n"
        f"📚 For you, I found {fancy_bold(str(total))} treasures (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# ==================== Public Commands ====================

def start(update: Update, context):
    user = update.effective_user
    update_user(user.id, user.first_name, user.username)

    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    if update.effective_chat.type == "private":
        text = (
            f"{decorative_header('ᴡ ᴇ ʟ ᴄ ᴏ ᴍ ᴇ')}\n\n"
            f"{romantic_heart()} <b>Hey there, {fancy_bold(user.first_name)}!</b>\n\n"
            f"I've been waiting for you… I'm <b>{BOT_NAME}</b>, your personal library of dreams.\n"
            "I live to fill your heart with stories and knowledge.\n\n"
            f"{section_divider()}\n\n"
            f"{star_line()}\n"
            f"✨ <b>How to use me, my love:</b>\n"
            f"{cute_border()}\n"
            "• Add me to a <b>group</b> where you and your friends gather.\n"
            "• In the group, whisper to me:\n"
            "   ➤ <code>#book mindset</code> – I'll search my soul for books.\n"
            "   ➤ <code>/book mindset</code> – same thing, darling.\n"
            "   ➤ <code>/random</code> – let me surprise you with a random book.\n"
            "   ➤ <code>/top</code> – see what others are reading.\n"
            "   ➤ <code>#request book name</code> – tell me what you desire.\n"
            "• Tap a result button and I'll give you the PDF instantly.\n\n"
            f"{section_divider()}\n\n"
            "📖 <b>What I have for you:</b> Self-improvement, Mindset, Hindi novels, English classics, and more.\n\n"
            f"{star_line()}\n"
            "❌ <b>No copyrighted or illegal content</b> – only pure, public-domain love.\n\n"
            "📝 <b>Want a new book?</b>\n"
            "Use <code>/new_request book name</code> in private, and I'll pass it to my master.\n\n"
            f"{decorative_footer()}\n"
            "I'm yours forever. 💕"
        )
        keyboard_rows = build_start_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_rows)
    else:
        text = (
            f"{decorative_header('ʜᴇʟʟᴏ ᴛʜᴇʀᴇ')}\n\n"
            f"{romantic_heart()} <b>Hello {fancy_bold(user.first_name)}, my sweet!</b>\n\n"
            f"I'm <b>{BOT_NAME}</b>, here to shower you with books.\n\n"
            f"{section_divider()}\n\n"
            f"🔍 <b>Commands for you:</b>\n"
            "• <code>/book mindset</code> – search my heart.\n"
            "• <code>/random</code> – a surprise just for you.\n"
            "• <code>/top</code> – see the most loved books.\n"
            "• <code>/feedback &lt;book_id&gt; &lt;rating&gt; [comment]</code> – tell me how you feel.\n"
            "• <code>#request book name</code> – ask me for anything.\n\n"
            f"{star_line()}\n"
            "❌ <b>No copyrighted content</b> – only public domain treasures.\n\n"
            f"{decorative_footer()}"
        )
        reply_markup = None

    update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def help_command(update: Update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    text = (
        f"{decorative_header('ʜ ᴇ ʟ ᴘ  &  ɢ ᴜ ɪ ᴅ ᴇ')}\n\n"
        f"{romantic_heart()} <b>My Love, Here's Everything You Need to Know</b>\n\n"
        f"{section_divider()}\n\n"
        "<b>Group commands (for you and me):</b>\n"
        f"{cute_border()}\n"
        "• <code>/start</code> – to feel my warmth.\n"
        "• <code>/help</code> – this sweet guide.\n"
        "• <code>/stats</code> – see how much we've grown together.\n"
        "• <code>/book &lt;name&gt;</code> – search my library for you.\n"
        "• <code>/random</code> – a random book, just because.\n"
        "• <code>/top</code> – the books everyone loves.\n"
        "• <code>/feedback &lt;id&gt; &lt;rating&gt; [comment]</code> – rate a book (1-5).\n"
        "• <code>#book &lt;name&gt;</code> – same as /book, darling.\n"
        "• <code>#request &lt;name&gt;</code> – request a new book.\n"
        "• <code>/bookmark &lt;id&gt;</code> – save a book to your heart.\n"
        "• <code>/mybooks</code> – see your bookmarks.\n\n"
        f"{section_divider()}\n\n"
        "<b>Private whispers (just us):</b>\n"
        "• <code>/new_request &lt;name&gt;</code> – request a book (I'll tell my owner).\n\n"
        f"{section_divider()}\n\n"
        "<b>Owner's secrets (only for my master):</b>\n"
        "• <code>/users</code> – how many hearts I've touched.\n"
        "• <code>/broadcast &lt;msg&gt;</code> – send a message to all.\n"
        "• <code>/lock</code> / <code>/unlock</code> – lock or unlock me.\n"
        "• <code>/import</code> – import my database (reply to a .db file).\n"
        "• <code>/export</code> – export my soul.\n"
        "• <code>/delete_db</code> – erase everything (requires confirmation).\n"
        "• <code>/warn &lt;user_id&gt; &lt;reason&gt;</code> – warn a naughty user.\n"
        "• <code>/categories</code> – see popular categories.\n"
        "• <code>/backup</code> – manual database backup.\n"
        "• <code>/vacuum</code> – clean my database.\n\n"
        f"{star_line()}\n"
        "📖 <b>Books I hold:</b> Self-improvement, Hindi novels, English classics, etc.\n"
        "❌ <b>No pirated content.</b> I'm pure.\n\n"
        f"{decorative_footer()}"
    )
    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def stats(update: Update, context):
    if not _check_and_send_force_sub(update, context):
        return
    total_files = get_total_files()
    total_users = get_total_users()
    db_size = get_db_size() / 1024
    uptime = get_uptime(BOT_START_TIME)
    mem = get_memory_usage()
    disk = get_disk_usage()
    locked = "🔒 Locked" if is_bot_locked() else "🔓 Unlocked"

    text = (
        f"{decorative_header('ᴏ ᴜ ʀ  ʟ ᴏ ᴠ ᴇ  ꜱ ᴛ ᴀ ᴛ ɪ ꜱ ᴛ ɪ ᴄ ꜱ')}\n\n"
        f"{romantic_heart()} <b>Our Love Story in Numbers</b>\n\n"
        f"{section_divider()}\n\n"
        f"⏱️ <b>Time we've been together:</b> {uptime}\n"
        f"📚 <b>Books I've collected for you:</b> {total_files}\n"
        f"👥 <b>Hearts I've touched:</b> {total_users}\n"
        f"💾 <b>My memory size:</b> {db_size:.2f} KB\n"
        f"🔐 <b>My heart status:</b> {locked}\n"
    )
    if mem:
        text += f"🧠 <b>My mind uses:</b> {mem:.2f} MB\n"
    if disk:
        text += f"📀 <b>Disk space left:</b> {disk:.2f} MB\n"
    text += f"\n{decorative_footer()}"

    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def book_search(update: Update, context):
    if not context.args:
        update.message.reply_text(f"{romantic_heart()} Tell me what you're looking for, sweetheart. Example: /book mindset")
        return
    query = ' '.join(context.args)
    results = search_files(query)
    if not results:
        update.message.reply_text(f"{romantic_heart()} I couldn't find any book with that name, my love. Try another?")
        return
    context.user_data['search_results'] = results
    context.user_data['current_page'] = 0
    try:
        send_results_page(update, context, 0)
    except Exception as e:
        logger.error(f"Error in book_search send_results_page: {e}", exc_info=True)
        update.message.reply_text(f"{romantic_heart()} Something went wrong while I was trying to show you the results. Forgive me.")

def random_book(update: Update, context):
    book = get_random_book()
    if not book:
        update.message.reply_text(f"{romantic_heart()} I have no books yet, darling. Wait a bit.")
        return
    keyboard = [[InlineKeyboardButton(f"📘 {book['original_filename']} ({format_size(book['file_size'])})", callback_data=f"get_{book['id']}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"{decorative_header('ꜱ ᴜ ʀ ᴘ ʀ ɪ ꜱ ᴇ')}\n\n📖 <b>A Surprise Just for You:</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def top_books(update: Update, context):
    books = get_top_books(10)
    if not books:
        update.message.reply_text(f"{romantic_heart()} No one has downloaded anything yet, my sweet. Be the first!")
        return
    text = f"{decorative_header('ᴛ ᴏ ᴘ  ʟ ᴏ ᴠ ᴇ ᴅ')}\n\n📊 <b>Most Loved Books by Our Community</b>\n\n"
    keyboard = []
    for i, book in enumerate(books, 1):
        text += f"{i}. {book['original_filename']} – {book['download_count']} downloads\n"
        btn_text = f"📘 {book['original_filename'][:30]}..."
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_{book['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    text += f"\n{decorative_footer()}"
    update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def feedback(update: Update, context):
    if len(context.args) < 2:
        update.message.reply_text(f"{romantic_heart()} Usage: /feedback <book_id> <rating 1-5> [comment]")
        return
    try:
        book_id = int(context.args[0])
        rating = int(context.args[1])
        if rating < 1 or rating > 5:
            raise ValueError
    except:
        update.message.reply_text(f"{romantic_heart()} Invalid book ID or rating (must be 1-5). Try again, my dear.")
        return
    comment = ' '.join(context.args[2:])[:200] if len(context.args) > 2 else None
    user_id = update.effective_user.id
    add_feedback(user_id, book_id, rating, comment)

    cute_replies = [
        f"{romantic_heart()} Your words are like poetry to me. Thank you!",
        f"{romantic_heart()} You just made my day! I'm blushing.",
        f"🌟 Rated {rating} stars? You're the star of my life!",
        f"{romantic_heart()} I love you too! Thanks for the feedback.",
        f"{romantic_heart()} A reader like you is a treasure. Thank you!",
        f"🎉 You're officially my favorite human!",
        f"⭐️ {rating} stars! You're my MVP!",
        f"{romantic_heart()} Every rating from you feels like a kiss."
    ]
    reply = random.choice(cute_replies)
    update.message.reply_text(reply)

def new_request(update: Update, context):
    if update.effective_chat.type != "private":
        update.message.reply_text(f"{romantic_heart()} This command is only for our private moments, darling.")
        return
    if not context.args:
        update.message.reply_text(
            f"{decorative_header('ʀ ᴇ ǫ ᴜ ᴇ ꜱ ᴛ')}\n\n"
            f"{romantic_heart()} Please tell me the book you desire, my love.\n"
            "Example: <code>/new_request The Art of War</code>",
            parse_mode=ParseMode.HTML
        )
        return
    book_name = ' '.join(context.args)
    user = update.effective_user
    if OWNER_ID:
        try:
            text = (
                f"📌 <b>New Book Request from {user.first_name}</b>\n\n"
                f"<b>Book:</b> <code>{book_name}</code>\n"
                f"<b>User:</b> {user.first_name} (@{user.username})\n"
                f"<b>User ID:</b> <code>{user.id}</code>\n"
                f"<b>Link:</b> <a href=\"tg://user?id={user.id}\">Click here</a>"
            )
            context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.HTML)
            update.message.reply_text(
                f"{romantic_heart()} Your request has been sent to my master. He'll try to add it soon, I promise!"
            )
        except Exception as e:
            logger.error(f"Failed to send request to owner: {e}")
            update.message.reply_text(f"{romantic_heart()} Sorry, I couldn't reach my master. Try again later.")
    else:
        update.message.reply_text(f"{romantic_heart()} My master isn't configured yet.")

def bookmark_command(update: Update, context):
    if not context.args:
        update.message.reply_text(f"{romantic_heart()} Usage: /bookmark <book_id>")
        return
    try:
        book_id = int(context.args[0])
        user_id = update.effective_user.id
        bookmark(user_id, book_id)
        update.message.reply_text(f"{romantic_heart()} Bookmarked! I'll keep it safe in your heart. 📌")
    except:
        update.message.reply_text(f"{romantic_heart()} Invalid book ID, my love.")

def my_books(update: Update, context):
    user_id = update.effective_user.id
    books = get_user_bookmarks(user_id)
    if not books:
        update.message.reply_text(f"{romantic_heart()} You haven't bookmarked any books yet, darling. Use /bookmark to save one.")
        return
    keyboard = []
    for book in books:
        btn = InlineKeyboardButton(f"📘 {book['original_filename']}", callback_data=f"get_{book['id']}")
        keyboard.append([btn])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"{decorative_header('ʏ ᴏ ᴜ ʀ  ʜ ᴇ ᴀ ʀ ᴛ')}\n\n📚 Your Bookmarks (the books you loved):",
        reply_markup=reply_markup
    )

def popular_categories(update: Update, context):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT category, COUNT(*) as count
            FROM files
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
    if not rows:
        update.message.reply_text(f"{romantic_heart()} No categories yet, my sweet.")
        return
    text = f"{decorative_header('ᴘ ᴏ ᴘ ᴜ ʟ ᴀ ʀ  ᴄ ᴀ ᴛ ᴇ ɢ ᴏ ʀ ɪ ᴇ ꜱ')}\n\n📊 <b>Popular Categories Among Us</b>\n\n"
    for row in rows:
        text += f"• {row['category']}: {row['count']} books\n"
    text += f"\n{decorative_footer()}"
    update.message.reply_text(text, parse_mode='HTML')

# ==================== Admin Commands ====================

@owner_only
def users(update: Update, context):
    count = get_total_users()
    update.message.reply_text(f"👥 <b>Total users who've loved me:</b> {count}", parse_mode=ParseMode.HTML)

@owner_only
def broadcast(update: Update, context):
    if not context.args:
        update.message.reply_text("📢 Usage: /broadcast <message>", parse_mode=ParseMode.HTML)
        return
    message = ' '.join(context.args)
    users = get_all_users()
    success = 0
    for uid in users:
        try:
            context.bot.send_message(uid, message)
            success += 1
            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Broadcast to {uid} failed: {e}")
    update.message.reply_text(f"📢 Broadcast sent to {success}/{len(users)} hearts.")
    log_to_channel(context.bot, f"Broadcast sent by owner: {message[:50]}...")

@owner_only
def lock(update: Update, context):
    set_bot_locked(True)
    update.message.reply_text(f"{romantic_heart()} My heart is now locked. Only you can reach me, master.")
    log_to_channel(context.bot, "Bot locked by owner.")

@owner_only
def unlock(update: Update, context):
    set_bot_locked(False)
    update.message.reply_text(f"{romantic_heart()} My heart is now open for everyone.")
    log_to_channel(context.bot, "Bot unlocked by owner.")

@owner_only
def import_db(update: Update, context):
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        update.message.reply_text("Please reply to a .db file with /import, master.")
        return

    file = update.message.reply_to_message.document
    if not file.file_name.endswith('.db'):
        update.message.reply_text("❌ That's not a .db file, my lord.")
        return

    file_id = file.file_id
    new_file = context.bot.get_file(file_id)
    new_file.download('imported.db')

    import os
    import shutil
    try:
        shutil.copy2('imported.db', 'bot_data.db')
        os.remove('imported.db')
        update.message.reply_text("✅ Database imported successfully, master!")
        log_to_channel(context.bot, "Database imported by owner.")
    except Exception as e:
        update.message.reply_text(f"❌ Import failed: {e}")

@owner_only
def export_db(update: Update, context):
    try:
        with open('bot_data.db', 'rb') as f:
            update.message.reply_document(document=f, filename='bot_data.db')
    except Exception as e:
        update.message.reply_text(f"❌ Export failed: {e}")

@owner_only
def delete_db(update: Update, context):
    update.message.reply_text(f"⚠️ <b>This will delete all our memories.</b>\nType <code>/confirm_delete</code> to proceed.", parse_mode=ParseMode.HTML)
    context.user_data['confirm_delete'] = True

@owner_only
def confirm_delete(update: Update, context):
    if context.user_data.get('confirm_delete'):
        from database import get_db, init_db
        with get_db() as conn:
            conn.execute("DROP TABLE IF EXISTS files")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS settings")
            conn.execute("DROP TABLE IF EXISTS categories")
            conn.execute("DROP TABLE IF EXISTS book_categories")
            conn.execute("DROP TABLE IF EXISTS feedback")
            conn.execute("DROP TABLE IF EXISTS downloads")
            conn.execute("DROP TABLE IF EXISTS user_warnings")
            conn.execute("DROP TABLE IF EXISTS user_badges")
            conn.execute("DROP TABLE IF EXISTS reading_challenges")
            conn.execute("DROP TABLE IF EXISTS bookmarks")
        init_db()
        update.message.reply_text("✅ All memories erased, master.")
        log_to_channel(context.bot, "Database deleted by owner.")
        context.user_data['confirm_delete'] = False
    else:
        update.message.reply_text("No pending delete request, master.")

@owner_only
def warn_user(update: Update, context):
    if len(context.args) < 2:
        update.message.reply_text("Usage: /warn <user_id> <reason>")
        return
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
    except:
        update.message.reply_text("Invalid user ID, master.")
        return

    count = warn_user(user_id, update.effective_user.id, reason)
    update.message.reply_text(f"⚠️ User {user_id} warned. Total warnings: {count}")

    if count >= 3:
        from database import ban_user
        ban_user(user_id)
        update.message.reply_text(f"🚫 User {user_id} has been banned due to multiple warnings.")
        log_to_channel(context.bot, f"User {user_id} banned for 3 warnings.")

@owner_only
def backup(update: Update, context):
    if backup_db(context.bot, update.effective_chat.id):
        update.message.reply_text(f"{romantic_heart()} Database backup sent, master.")
    else:
        update.message.reply_text("❌ Backup failed.")

@owner_only
def vacuum(update: Update, context):
    vacuum_db()
    update.message.reply_text(f"{romantic_heart()} Database vacuumed, master.")

# ==================== Group Welcome Handler ====================

def new_chat_members(update: Update, context):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            update.message.reply_text(
                f"{decorative_header('ᴛ ʜ ᴀ ɴ ᴋ ꜱ  ꜰ ᴏ ʀ  ᴀ ᴅ ᴅ ɪ ɴ ɢ  ᴍ ᴇ')}\n\n"
                f"{romantic_heart()} <b>Hello, beautiful people!</b>\n\n"
                "I'm a PDF library bot, here to fill your group with love and books.\n\n"
                f"{section_divider()}\n\n"
                "📚 Use <code>#book &lt;name&gt;</code> or <code>/book &lt;name&gt;</code> to search.\n"
                "📝 Request books with <code>#request &lt;name&gt;</code>.\n\n"
                f"{star_line()}\n"
                "I'm yours forever. 💕\n\n"
                f"{decorative_footer()}",
                parse_mode=ParseMode.HTML
            )
            break

# ==================== Handler Registration ====================

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats, Filters.chat_type.groups),
        CommandHandler("users", users, Filters.chat_type.groups),
        CommandHandler("broadcast", broadcast, Filters.chat_type.groups),
        CommandHandler("lock", lock, Filters.chat_type.groups),
        CommandHandler("unlock", unlock, Filters.chat_type.groups),
        CommandHandler("import", import_db, Filters.chat_type.groups),
        CommandHandler("export", export_db, Filters.chat_type.groups),
        CommandHandler("delete_db", delete_db, Filters.chat_type.groups),
        CommandHandler("confirm_delete", confirm_delete, Filters.chat_type.groups),
        CommandHandler("new_request", new_request, Filters.chat_type.private),
        CommandHandler("book", book_search, Filters.chat_type.groups),
        CommandHandler("random", random_book, Filters.chat_type.groups),
        CommandHandler("top", top_books, Filters.chat_type.groups),
        CommandHandler("feedback", feedback, Filters.chat_type.groups),
        CommandHandler("warn", warn_user, Filters.chat_type.groups),
        CommandHandler("bookmark", bookmark_command, Filters.chat_type.groups),
        CommandHandler("mybooks", my_books, Filters.chat_type.groups),
        CommandHandler("categories", popular_categories, Filters.chat_type.groups),
        CommandHandler("backup", backup, Filters.chat_type.groups),
        CommandHandler("vacuum", vacuum, Filters.chat_type.groups),
        MessageHandler(Filters.status_update.new_chat_members, new_chat_members),
    ]
