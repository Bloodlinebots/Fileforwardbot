import asyncio
import logging
import os
from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for ConversationHandler
SOURCE_CHANNEL, TARGET_CHANNEL, START_ID, END_ID = range(4)

# Temporary user storage
user_data = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome!\nUse /connect to begin media forwarding setup.")

# /connect command handler
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Please send the source channel ID (e.g., -100xxxxxxxxxx):")
    return SOURCE_CHANNEL

# Step 1: Source channel ID
async def source_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        source_id = int(update.message.text)
        member = await context.bot.get_chat_member(chat_id=source_id, user_id=context.bot.id)
        if member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            user_data[user_id] = {"source": source_id}
            await update.message.reply_text("✅ Source channel connected!\nNow send the target channel ID:")
            return TARGET_CHANNEL
        else:
            await update.message.reply_text("❌ Bot is not an admin in the source channel.")
            return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Invalid source channel ID or bot not present.")
        return ConversationHandler.END

# Step 2: Target channel ID
async def target_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        target_id = int(update.message.text)
        member = await context.bot.get_chat_member(chat_id=target_id, user_id=context.bot.id)
        if member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            user_data[user_id]["target"] = target_id
            await update.message.reply_text("🔢 Send the START message ID:")
            return START_ID
        else:
            await update.message.reply_text("❌ Bot is not an admin in the target channel.")
            return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Invalid target channel ID or bot not present.")
        return ConversationHandler.END

# Step 3: Start message ID
async def start_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["start_id"] = int(update.message.text)
        await update.message.reply_text("🔢 Now send the END message ID:")
        return END_ID
    except:
        await update.message.reply_text("❌ Invalid start message ID.")
        return ConversationHandler.END

# Step 4: End message ID and start forwarding
async def end_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        user_data[user_id]["end_id"] = int(update.message.text)

        source = user_data[user_id]["source"]
        target = user_data[user_id]["target"]
        start_id = user_data[user_id]["start_id"]
        end_id = user_data[user_id]["end_id"]

        await update.message.reply_text("🚀 Forwarding started...")

        for msg_id in range(start_id, end_id + 1):
            try:
                await context.bot.copy_message(chat_id=target, from_chat_id=source, message_id=msg_id)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"⚠️ Failed to forward message {msg_id}: {e}")
                continue

        await update.message.reply_text("✅ Forwarding completed successfully!")
        return ConversationHandler.END

    except:
        await update.message.reply_text("❌ Invalid end message ID.")
        return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Forwarding setup canceled.")
    return ConversationHandler.END

# Main
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN")  # Set your token in Heroku or .env file

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("connect", connect)],
        states={
            SOURCE_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, source_channel)],
            TARGET_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_channel)],
            START_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_id)],
            END_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("🚀 Bot is running...")
    app.run_polling()
