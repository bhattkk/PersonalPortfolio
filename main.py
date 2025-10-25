import asyncio
from messaging.telegram_bot import TelegramBot
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from kite.portfolio_report import KiteWrapper


def load_config():
    with open("config.yaml", 'r') as file:
        return yaml.safe_load(file)

def tTelegramBot():
    config = load_config()
    telegram_config = config.get("telegram_bot", {})
    token = telegram_config.get("token", "")
    chat_id = telegram_config.get("chat_id", 0)
    if not token or not chat_id:
        print("Telegram bot token or chat_id not found in config.yaml")
        return
    return TelegramBot(token, chat_id)

async def main():
    bot = tTelegramBot() # Telegram Bot
    kiteWrapper = KiteWrapper(bot)  # Initialize KiteWrapper with the bot instance
    #start_scheduler(kiteWrapper)  # Start the scheduler
    await bot.run()  # Keep the main function running
    
if __name__ == "__main__":
    asyncio.run(main())
