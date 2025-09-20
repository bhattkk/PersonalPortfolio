import asyncio
import logging
from datetime import datetime, time
from typing import Dict, Callable, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class TelegramBot:
    """
    A flexible Telegram bot class with command handling and scheduling capabilities.
    
    Features:
    - Command registration and handling
    - Scheduled messages
    - Easy extensibility
    - Proper error handling and logging
    """
    
    def __init__(self, token: str, chat_id: int):
        """
        Initialize the Telegram bot.
        
        Args:
            token (str): Bot token from BotFather
            chat_id (int): Your chat ID to receive scheduled messages
        """
        self.token = token
        self.chat_id = chat_id
        self.application = Application.builder().token(token).build()
        self.scheduler = AsyncIOScheduler()
        self.commands: Dict[str, Callable] = {}
        self.Callbacks = {}
        
        # Configure logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
        # Register default commands
        self._register_default_commands()
        
    def register_callback(self, name: str, func: Callable):
        """
        Register a callback function for custom events.
        
        Args:
            name (str): Name of the callback
            func (Callable): Function to be called
        """
        self.Callbacks[name] = func
        self.logger.info(f"Registered callback: {name}")

    def _register_default_commands(self):
        """Register default bot commands."""
        self.add_command('start', self._start_command, 'Start the bot')
        self.add_command('help', self._help_command, 'Show available commands')
        self.add_command('ping', self._ping_command, 'Check if bot is responsive')
        
    def add_command(self, command: str, handler: Callable, description: str = ''):
        """
        Add a command to the bot.
        
        Args:
            command (str): Command name (without /)
            handler (Callable): Function to handle the command
            description (str): Description of the command for help
        """
        self.commands[command] = {
            'handler': handler,
            'description': description
        }
        self.application.add_handler(CommandHandler(command, handler))
        self.logger.info(f"Registered command: /{command}")
        
    def add_scheduled_message(self, hour: int, minute: int, message: str, timezone: str = None):
        """
        Schedule a daily message.
        
        Args:
            hour (int): Hour to send message (0-23)
            minute (int): Minute to send message (0-59)
            message (str): Message to send
            timezone (str): Timezone (e.g., 'Asia/Kolkata'), None for local
        """
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)
        
        async def send_scheduled_message():
            try:
                await self.application.bot.send_message(
                    chat_id=self.chat_id, 
                    text=message
                )
                self.logger.info(f"Scheduled message sent: {message}")
            except Exception as e:
                self.logger.error(f"Failed to send scheduled message: {e}")
        
        self.scheduler.add_job(
            send_scheduled_message,
            trigger=trigger,
            id=f"scheduled_msg_{hour}_{minute}"
        )
        self.logger.info(f"Scheduled daily message at {hour:02d}:{minute:02d}")
    
    def send_message(self, message: str, chat_id: int = None):
        """
        Send a message to specified chat or default chat.
        
        Args:
            message (str): Message to send
            chat_id (int): Chat ID to send to (uses default if None)
        """
        target_chat = chat_id or self.chat_id
        try:
            self.application.bot.send_message(chat_id=target_chat, text=message)
            self.logger.info(f"Message sent to {target_chat}: {message}")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")

    def send_csv(self, file_path: str):
        with open(file_path, "rb") as f:
            self.bot.send_document(self.chat_id, document=f)


    # Default command handlers
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_msg = (
            "🤖 Welcome to your personal Telegram bot!\n\n"
            "I'm here to help you with various tasks. "
            "Use /help to see available commands."
        )
        await update.message.reply_text(welcome_msg)
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = "📋 **Available Commands:**\n\n"
        
        for cmd, info in self.commands.items():
            description = info.get('description', 'No description')
            help_text += f"/{cmd} - {description}\n"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ping command."""
        await update.message.reply_text("🏓 Pong! Bot is running smoothly.")
    
    def setup_morning_greeting(self):
        """Setup default morning greeting at 7:00 AM."""
        morning_messages = [
            "🌅 Good morning! Hope you have a wonderful day ahead!",
            "☀️ Rise and shine! It's a new day full of possibilities!",
            "🌻 Good morning! Wishing you a productive and happy day!",
            "🎉 Good morning! Ready to make today amazing?"
        ]
        
        import random
        message = random.choice(morning_messages)
        self.add_scheduled_message(7, 0, message)
    
    async def run(self):
        """Start the bot and scheduler."""
        try:
            # Start scheduler
            self.scheduler.start()
            self.logger.info("Scheduler started")
            
            # Setup default morning greeting
            self.setup_morning_greeting()
            
            # Start bot
            self.logger.info("Starting Telegram bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            # Keep running
            await asyncio.Event().wait()
            
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
        finally:
            self.scheduler.shutdown()
            self.logger.info("Bot stopped")

    def stop(self):
        """Stop the bot and scheduler."""
        self.scheduler.shutdown()
        self.application.stop()
        self.logger.info("Bot stopped manually")


# # Usage example
# async def TelegramBotHandler(token: str, chat_id: int):
#     # Create bot instance
    
    
#     # Add custom commands (modify these as needed)
#     #async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     #    await update.message.reply_text("🌤️ Weather feature - customize this!")
    
#     #async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#         # if context.args:
#         #     reminder_text = ' '.join(context.args)
#         #     await update.message.reply_text(f"⏰ Reminder set: {reminder_text}")
#         # else:
#         #     await update.message.reply_text("Usage: /reminder Buy groceries")
    
#     # Register custom commands
#     #bot.add_command('weather', weather_command, 'Get weather info')
#     #bot.add_command('reminder', reminder_command, 'Set a reminder')
    
#     # Add more scheduled messages (customize as needed)
#     #bot.add_scheduled_message(12, 0, "🍽️ Lunch time! Don't forget to eat.")
#     #bot.add_scheduled_message(20, 0, "🌙 Good evening! Time to relax.")
    
#     # Run the bot
#     await bot.run()
