import asyncio
from telegram import Update, ChatMember, Chat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import logging
import os

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
SOURCE_CHANNEL, TARGET_CHANNEL, START_ID, END_ID = range(4)

# Temporary storage
user_data = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /connect to start forwarding setup.")

# /connect handler
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the source channel ID (e.g. -100xxxxxx):")
    return SOURCE_CHANNEL

# Step 1: Source channel ID
async def source_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    source_id = int(update.message.text)
    try:
        member = await context.bot.get_chat_member(chat_id=source_id, user_id=context.bot.id)
        if member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            user_data[user_id] = {"source": source_id}
            await update.message.reply_text("✅ Connected to source channel!\nNow send the target channel ID:")
            return TARGET_CHANNEL
        else:
            await update.message.reply_text("❌ Bot is not admin in source channel.")
            return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Invalid source channel ID or bot not in channel.")
        return ConversationHandler.END

# Step 2: Target channel ID
async def target_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_id = int(update.message.text)
    try:
        member = await context.bot.get_chat_member(chat_id=target_id, user_id=context.bot.id)
        if member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            user_data[user_id]["target"] = target_id
            await update.message.reply_text("🎯 Target channel set!\nNow send the START message ID:")
            return START_ID
        else:
            await update.message.reply_text("❌ Bot is not admin in target channel.")
            return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Invalid target channel ID or bot not in channel.")
        return ConversationHandler.END

# Step 3: Start message ID
async def start_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id]["start_id"] = int(update.message.text)
    await update.message.reply_text("Send the END message ID:")
    return END_ID

# Step 4: End message ID & Start forwarding
async def end_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id]["end_id"] = int(update.message.text)

    source = user_data[user_id]["source"]
    target = user_data[user_id]["target"]
    start_id = user_data[user_id]["start_id"]
    end_id = user_data[user_id]["end_id"]

    await update.message.reply_text("🚀 Done! Your bot started forwarding...")

    for msg_id in range(start_id, end_id + 1):
        try:
            msg = await context.bot.forward_message(chat_id=target, from_chat_id=source, message_id=msg_id)
            await asyncio.sleep(0.5)  # Delay to avoid flood
        except Exception as e:
            logger.error(f"Error forwarding msg_id {msg_id}: {e}")
            continue

    await update.message.reply_text("✅ Forwarding completed!")
    return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Forwarding setup canceled.")
    return ConversationHandler.END

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN")  # Use your real token or set in .env

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

    print("Bot is running...")
    app.run_polling()
