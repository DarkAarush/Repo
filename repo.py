import os
import shutil
import subprocess
import tempfile
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"

# --- Heroku API helpers ---
def get_heroku_apps(api_key):
    url = "https://api.heroku.com/apps"
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def clone_and_zip_repo(app_name):
    repo_url = f"https://git.heroku.com/{app_name}.git"
    temp_dir = tempfile.mkdtemp()
    app_dir = os.path.join(temp_dir, app_name)

    subprocess.run(["git", "clone", repo_url, app_dir], check=True)
    zip_path = shutil.make_archive(app_dir, 'zip', app_dir)
    return zip_path, temp_dir

# --- Telegram Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! I can help you download your Heroku apps.\n\n"
        "Use these commands:\n"
        "• /repos <HEROKU_API_KEY> — List all your apps\n"
        "• /download <API_KEY> <APP_NAME> — Download a specific app\n"
        "Or just send your API key to download all apps."
    )

async def repos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Usage: /repos <HEROKU_API_KEY>")
        return

    api_key = context.args[0]

    try:
        apps = get_heroku_apps(api_key)
        if not apps:
            await update.message.reply_text("No apps found.")
            return

        app_names = "\n".join([f"• {app['name']}" for app in apps])
        await update.message.reply_text(f"🗂 Your Heroku Apps:\n{app_names}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗ Usage: /download <HEROKU_API_KEY> <APP_NAME>")
        return

    api_key = context.args[0]
    app_name = context.args[1]

    try:
        await update.message.reply_text(f"📦 Downloading {app_name}...")
        zip_file, temp_dir = clone_and_zip_repo(app_name)
        with open(zip_file, 'rb') as f:
            await update.message.reply_document(document=f, filename=f"{app_name}.zip")
        shutil.rmtree(temp_dir, ignore_errors=True)
    except subprocess.CalledProcessError:
        await update.message.reply_text(f"❌ Failed to clone {app_name}. Make sure the app exists and you have access.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = update.message.text.strip()
    await update.message.reply_text("🔍 Fetching apps...")

    try:
        apps = get_heroku_apps(api_key)
        if not apps:
            await update.message.reply_text("No apps found.")
            return

        for app in apps:
            name = app['name']
            await update.message.reply_text(f"📦 Zipping: {name}")
            try:
                zip_file, temp_dir = clone_and_zip_repo(name)
                with open(zip_file, 'rb') as f:
                    await update.message.reply_document(document=f, filename=f"{name}.zip")
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to clone {name}: {str(e)}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        await update.message.reply_text("✅ All apps processed.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# --- Run bot ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("repos", repos))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_key))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
