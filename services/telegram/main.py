"""
Telegram service: single bot process.
- Poll Telegram; handle /login, /token, /watchlist, /refresh_sd, /help, /ping.
- Consume Redis stream telegram:outbound (login URL + portfolio report); send to chat.
- Reply context in Redis only: /token writes to context; kite-portfolio reads from Redis.
"""
import asyncio
import logging
import os
import redis

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from redis_outbound import (
    consume_outbound_loop,
    get_context_id_for_chat,
    set_reply_context_token,
    get_redis,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))


def get_sync_redis():
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📋 **Available Commands:**\n\n"
        "/help - Show this message\n"
        "/ping - Check if bot is responsive\n"
        "/login - Start Kite login flow (get URL, then /token <request_token>)\n"
        "/token <request_token> - Submit request token after login\n"
        "/watchlist - Refresh and send portfolio watchlist\n"
        "/refresh_sd - Refresh static instrument data\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot is running smoothly.")


async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Login: we only tell user to use /login; kite-portfolio pushes URL via stream with reply_context."""
    await update.message.reply_text(
        "Login is handled by kite-portfolio. Requesting login URL... "
        "You will receive a message with the URL; then use /token <request_token>."
    )
    # Notify via Redis that login was requested (kite-portfolio can listen or we push a command stream)
    r = get_sync_redis()
    r.publish("telegram:commands", "login")


async def cmd_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /token <request_token>")
        return
    request_token = context.args[0]
    chat_id = update.effective_chat.id if update.effective_chat else CHAT_ID
    r = get_sync_redis()
    context_id = get_context_id_for_chat(r, chat_id)
    if not context_id:
        await update.message.reply_text(
            "⚠️ No pending login. Use /login first to get the login URL, then use /token <request_token>."
        )
        return
    set_reply_context_token(r, context_id, request_token)
    await update.message.reply_text("✔ Token received and processed.")


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = get_sync_redis()
    r.publish("telegram:commands", "watchlist")
    await update.message.reply_text("Requesting watchlist refresh... You will receive the report when ready.")


async def cmd_refresh_sd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = get_sync_redis()
    r.publish("telegram:commands", "refresh_sd")
    await update.message.reply_text("Requesting static data refresh... You will receive a confirmation when done.")


def main():
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
        logger.error("Set TELEGRAM_BOT_TOKEN and CHAT_ID")
        raise SystemExit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("token", cmd_token))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("refresh_sd", cmd_refresh_sd))

    async def run():
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Notify chat that bot started
        try:
            await app.bot.send_message(chat_id=CHAT_ID, text="🤖 Bot started and running!")
        except Exception as e:
            logger.warning("Could not send startup message: %s", e)
        # Start stream consumer in background
        consumer = asyncio.create_task(consume_outbound_loop(app))
        try:
            await asyncio.Event().wait()
        finally:
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    asyncio.run(run())


if __name__ == "__main__":
    main()
