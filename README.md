# 📚 PDF Library Bot – Telegram Book & PDF Bot

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0-blue.svg" />
  <img src="https://img.shields.io/badge/python-3.11-green.svg" />
  <img src="https://img.shields.io/badge/telegram-bot-2CA5E0.svg" />
  <img src="https://img.shields.io/badge/Render-deployed-success.svg" />
</p>

<p align="center">
  <b>A powerful Telegram bot that listens to source groups, stores PDF metadata, and provides instant book search with colourful inline buttons.</b>
</p>

---

## 📋 Table of Contents
- [✨ Features](#-features)
- [🤖 Bot Commands](#-bot-commands)
- [⚙️ Configuration](#️-configuration)
- [🚀 Deploy on Render](#-deploy-on-render)
- [📁 Project Structure](#-project-structure)
- [👨‍💻 Credits & License](#-credits--license)
- [📞 Support](#-support)

---

## ✨ Features

| | Feature | Description |
|---|---------|-------------|
| 📥 | **Auto-save PDFs** | Listens to multiple source groups/channels and stores metadata (file_id, name, size) without downloading files. |
| 🔍 | **Smart Search** | Search books using `#book <name>` or `/book <name>` with partial match support. |
| 🎛️ | **Colourful Inline Buttons** | Results displayed with original filename + file size in attractive buttons. |
| 📄 | **Pagination** | Navigate through multiple search results with next/prev buttons. |
| ❤️ | **Animated Reactions** | Every message gets random animated reactions (big/small emojis). |
| 📝 | **Book Requests** | Users can request books with `#request <name>` – owner gets notified. |
| 🔐 | **Force Subscribe** | Users must join a channel before using the bot. |
| 👤 | **Owner Contact** | Direct owner button in every menu. |
| 📢 | **Channel & Request Group** | Quick access buttons to your channel and request group. |
| 🛠️ | **Admin Commands** | Full suite of owner-only commands for management. |
| 🚀 | **Ready to Deploy** | Docker + Gunicorn setup for instant deployment on Render. |
| 💾 | **Lightweight** | Stores only metadata in SQLite – no PDF files saved. |

---

## 🤖 Bot Commands

### 👥 Public Commands

| Command | Description | Works In |
|---------|-------------|----------|
| `/start` | Welcome message with inline buttons | Private & Groups |
| `/help` | Help and command list | Private & Groups |
| `/stats` | Bot statistics (PDFs, users, uptime, etc.) | Groups |
| `/book <name>` | Search for a book | Groups |
| `#book <name>` | Alternative search tag | Groups |
| `#request <name>` | Request a book (notifies owner) | Groups |
| `/new_request <name>` | Request a book from private chat | Private |

### 🔒 Owner Only Commands

| Command | Description |
|---------|-------------|
| `/users` | Show total user count |
| `/broadcast <msg>` | Send message to all users |
| `/lock` | Lock bot (only owner can use) |
| `/unlock` | Unlock bot |
| `/export` | Export database file |
| `/delete_db` | Delete all data (requires confirmation) |
| `/confirm_delete` | Confirm database deletion |

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set these in Render dashboard:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOT_TOKEN` | ✅ | Bot token from [@BotFather](https://t.me/botfather) | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `OWNER_ID` | ✅ | Your Telegram numeric ID | `123456789` |
| `OWNER_USERNAME` | ✅ | Your Telegram username (with @) | `@Xioqui_xin` |
| `FORCE_SUB_CHANNEL` | ✅ | Channel users must join | `@serenaunzip` |
| `SOURCE_CHANNELS` | ✅ | Comma-separated numeric IDs of source groups | `-1003745290301,-1003412208912` |
| `LOG_CHANNEL` | ❌ | Channel ID for logs | `-1001234567890` |
| `REQUEST_GROUP` | ❌ | Link or @username for request group | `@requestgroup` |
| `BOT_NAME` | ❌ | Custom bot name | `📚 PDF Library Bot` |

> ⚠️ **Important**:  
> - `SOURCE_CHANNELS` must be **numeric IDs** (e.g., `-1001234567890`). Get them from [@getidsbot](https://t.me/getidsbot).  
> - Bot must be **a member** of these source groups.  
> - **Group Privacy must be OFF** for the bot to read messages (configure via BotFather).

---

## 🚀 Deploy on Render

### Step 1: Fork or Clone Repository
```bash
git clone https://github.com/SerenaXdev/pdf-library-bot.git
cd pdf-library-bot



Step 2: Push to Your GitHub
Step 3: Create New Web Service on Render
Go to Render Dashboard

Click New + → Web Service

Connect your GitHub repository

Configure:

Name: your-bot-name

Environment: Docker (auto-detected)

Region: choose closest

Branch: main

Build Command: leave blank

Start Command: leave blank

Instance Type: Free (or paid)

Step 4: Add Environment Variables
Add all variables from the Configuration section.

Step 5: Deploy
Click Create Web Service. Render will build and deploy your bot.

✅ After deployment, visit https://your-app.onrender.com/health to verify status.


👨‍💻 Credits & License
<p align="center"> <b>Created with ❤️ by <a href="https://github.com/SerenaXdev">SerenaXdev</a></b> </p>
text
© 2025 SerenaXdev. All Rights Reserved.
📝 Terms & Conditions
✅ You may use this code personally or for your own bot.

✅ You must give proper credit to the original author (SerenaXdev).

✅ You may modify the code for your needs.

❌ You may NOT claim this code as your own.

❌ You may NOT redistribute without credit.

❌ Commercial use requires explicit permission.

By using this code, you agree to these terms.

📞 Support
🐛 Found a bug? Open an issue

💬 Questions? Contact @Xioqui_xin

⭐ Like this project? Star on GitHub!





📊 Bot Statistics
Metric	Value
Python	3.11
Database	SQLite
Framework	python-telegram-bot v13.15
Hosting	Render (Docker)
File Size Limit	100 MB
<p align="center"> <b>📚 Happy Reading! 📚</b><br> <i>Made with ❤️ by SerenaXdev</i> </p> ```
