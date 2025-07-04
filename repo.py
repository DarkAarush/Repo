import os
import shutil
import subprocess
import tempfile
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = "7694420520:AAFUVzHmpcDValxWyWXku9gWG8J_qYXBtKA"  # Replace with your bot token

# Fetch all Heroku apps
def get_heroku_apps(api_key):
    url = "https://api.heroku.com/apps"
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Clone a Heroku app repo and return all file paths
def clone_and_get_files(app_name, api_key):
    repo_url = f"https://heroku:{api_key}@git.heroku.com/{app_name}.git"
    temp_dir = tempfile.mkdtemp()
    app_dir = os.path.join(temp_dir, app_name)

    subprocess.run(["git", "clone", repo_url, app_dir], check=True)

    file_paths = []
    for root, dirs, files in os.walk(app_dir):
        if '.git' in dirs:
            dirs.remove('.git')
        for file in files:
            if not file.startswith('.'):
                full_path = os.path.join(root, file)
                file_paths.append(full_path)

    return file_paths, temp_dir

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 Welcome! I can help you download your Heroku apps.\n\n"
            "Use these commands:\n"
            "• /repos <HEROKU_API_KEY> — List your apps\n"
            "• /download <API_KEY> <APP_NAME> — Download a specific app\n"
            "Or just send your API key to download all apps."
        )
    )

# /repos command
async def repos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❗ Usage: /repos <HEROKU_API_KEY>")
        return

    api_key = context.args[0]
    try:
        apps = get_heroku_apps(api_key)
        if not apps:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No apps found.")
            return

        app_names = "\n".join([f"• {app['name']}" for app in apps])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🗂 Your Heroku Apps:\n{app_names}")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {str(e)}")

# /download command
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❗ Usage: /download <HEROKU_API_KEY> <APP_NAME>")
        return

    api_key = context.args[0]
    app_name = context.args[1]

    try:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📦 Cloning `{app_name}`...", parse_mode="Markdown")
        file_paths, temp_dir = clone_and_get_files(app_name, api_key)

        if not file_paths:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❗ No files found in `{app_name}`.", parse_mode="Markdown")
        else:
            for file_path in file_paths[:20]:  # Limit to first 20 files
                try:
                    with open(file_path, 'rb') as f:
                        await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename=os.path.basename(file_path))
                except Exception as e:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Failed to send `{file_path}`: {str(e)}", parse_mode="Markdown")
        shutil.rmtree(temp_dir, ignore_errors=True)
    except subprocess.CalledProcessError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Failed to clone `{app_name}`. Check access or app name.", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Error: {str(e)}")

# Handle plain API key messages (download all apps)
async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = update.message.text.strip()
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="🔍 Fetching apps...")

    try:
        apps = get_heroku_apps(api_key)
        if not apps:
            await context.bot.send_message(chat_id=chat_id, text="No apps found.")
            return

        for app in apps:
            name = app['name']
            await context.bot.send_message(chat_id=chat_id, text=f"📦 Cloning `{name}`...", parse_mode="Markdown")
            try:
                file_paths, temp_dir = clone_and_get_files(name, api_key)
                if not file_paths:
                    await context.bot.send_message(chat_id=chat_id, text=f"❗ No files in `{name}`", parse_mode="Markdown")
                else:
                    for file_path in file_paths[:20]:
                        try:
                            with open(file_path, 'rb') as f:
                                await context.bot.send_document(chat_id=chat_id, document=f, filename=os.path.basename(file_path))
                        except Exception as e:
                            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error sending `{file_path}`: {str(e)}", parse_mode="Markdown")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to clone `{name}`: {str(e)}", parse_mode="Markdown")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        await context.bot.send_message(chat_id=chat_id, text="✅ All apps processed.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Error: {str(e)}")

# Main entry point
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
