import asyncio
from messaging.telegram_bot import TelegramBot
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from kite.portfolio_report import KiteWrapper


def load_config():
    with open("config.yaml", 'r') as file:
        return yaml.safe_load(file)

async def tTelegramBot():
    config = load_config()
    telegram_config = config.get("telegram_bot", {})
    token = telegram_config.get("token", "")
    chat_id = telegram_config.get("chat_id", 0)
    if not token or not chat_id:
        print("Telegram bot token or chat_id not found in config.yaml")
        return
    bot = TelegramBot(token, chat_id)
    # Initialize the Telegram bot with token and chat_id
    await bot.run()
    return bot

def start_scheduler(kiteWrapper):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(kiteWrapper.refresh_watchlist, "cron", hour=19, minute=0)  # Schedule at 7:00 PM daily
    scheduler.start()

async def main():
    bot_task = asyncio.create_task(tTelegramBot()) # Telegram Bot
    bot = await bot_task
    kiteWrapper = KiteWrapper(bot)  # Initialize KiteWrapper with the bot instance
    start_scheduler(bot)
    await asyncio.Event().wait()  # Keep the main function running
    

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
