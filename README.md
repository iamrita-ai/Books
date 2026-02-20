🚀 Deployment on Render
Push code to a GitHub repository.

Create a new Web Service on Render, connect your repo.

Set the Build Command to pip install -r requirements.txt.

Set the Start Command to gunicorn app:app.

Add all environment variables from .env.example in Render's dashboard.

Render will automatically provide the RENDER_EXTERNAL_URL variable, which will be used as the webhook base.

After deployment, the bot will set the webhook to https://your-app.onrender.com/webhook.

⚠️ Ensure your bot is allowed to receive updates via webhook; you may need to remove any previous webhook by visiting https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook.

🔧 Adding New Commands
Create a new function in handlers/commands.py (or a new module if preferred).

Decorate with @owner_only if it's admin-only.

Return a CommandHandler inside the get_handlers() function (or append to the list).

The new command will automatically be registered in app.py.

For example, to add a /ping command:

python
async def ping(update: Update, context):
    await update.message.reply_text("pong")

# Inside get_handlers(), add:
CommandHandler("ping", ping, filters=filters.ChatType.GROUPS)

📈 Performance & Scalability
Database: SQLite with indexes on normalized_name ensures fast partial searches.

No file storage: Only file_id is stored, so no disk usage for PDFs.

Pagination: Limits inline button rows to avoid hitting Telegram limits.

Webhook: Efficiently processes updates without polling.

Background thread: Separates asyncio bot logic from Flask's sync worker, allowing smooth operation.

✅ Summary
This bot meets all requirements:

Listens to source channel, ignores >100 MB, stores metadata only.

Group-only search with colorful inline buttons.

Force subscribe, owner contact, channel button, info button.

Reactions on every message.

Modular commands with /stats, /broadcast, etc.

Environment variables, no hardcoded secrets.

Ready for Render deployment with health check.
