import asyncio
import logging
from datetime import datetime, time
from typing import Dict, Callable, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class TelegramBot:
    def __init__(self, token: str, chat_id: int):
        self.token = token
        self.chat_id = chat_id
        self.application = Application.builder().token(token).build()
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

    async def send_message(self, message: str, chat_id: int = None):
        target_chat = chat_id or self.chat_id
        try:
            await self.application.bot.send_message(chat_id=target_chat, text=message)
            self.logger.info(f"Message sent to {target_chat}: {message}")
            #self.logger.debug(f"Telegram API response: {ret}")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")

    async def send_csv(self, file_path: str):
        with open(file_path, "rb") as f:
            await self.application.bot.send_document(self.chat_id, document=f)
        
    def register_callback(self, name: str, func: Callable):
        self.Callbacks[name] = func
        self.add_command(name, self._custom_command, f'Custom command: /{name}')
        self.logger.info(f"Registered callback: {name} to function: {func}" )

    # Default command handlers
    async def _custom_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /custom command."""
        welcome_msg = (
            "🤖 This is a cutom command"
        )
        
        # Get the command name without the leading '/'
        command_name = update.message.text.lstrip('/').split()[0]
        if command_name == 'watchlist':
            if 'watchlist' in self.Callbacks:
                success = await self.Callbacks['watchlist']()
                if not success:
                    welcome_msg = "⚠️ Failed to refresh watchlist. Please ensure you are logged in."
                else:
                    welcome_msg = "✔ Watchlist refreshed."
            else:
                welcome_msg = "⚠️ No callback registered for 'watchlist'."
        elif command_name == 'login':
            if 'login' in self.Callbacks:
                login_url = self.Callbacks['login']()
                welcome_msg = (
                    "✔ Login initiated. "
                    "Please provide the request token using /token <request_token>. "
                    "Login URL: " + login_url
                )
            else:
                welcome_msg = "⚠️ No callback registered for 'login'."
        elif command_name == 'token':
            if context.args:
                request_token = context.args[0]
                if 'token' in self.Callbacks:
                    self.Callbacks['token'](request_token)
                    welcome_msg = "✔ Token received and processed."
                else:
                    welcome_msg = "⚠️ No callback registered for 'token'."
            else:
                welcome_msg = "⚠️ Please provide a request token. Usage: /token <request_token>"
        elif command_name == 'refresh_sd':
            if 'refresh_sd' in self.Callbacks:
                success = await self.Callbacks['refresh_sd']()
                if not success:
                    welcome_msg = "⚠️ Failed to refresh static data. Please ensure you are logged in."
                else:
                    welcome_msg = "✔ Static data refreshed."
            else:
                welcome_msg = "⚠️ No callback registered for 'refresh_sd'."
        else:
            print("Unknown command:", command_name)
            welcome_msg = "⚠️ Unknown custom command."

        await update.message.reply_text(welcome_msg)
         
    def _register_default_commands(self):
        """Register default bot commands."""
        self.add_command('help', self._help_command, 'Show available commands')
        self.add_command('ping', self._ping_command, 'Check if bot is responsive')
        
    def add_command(self, command: str, handler: Callable, description: str = ''):
        self.commands[command] = {
            'handler': handler,
            'description': description
        }
        self.application.add_handler(CommandHandler(command, handler))
        self.logger.info(f"Registered command: /{command}")
    
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
    
    async def run(self):
        """Start the bot and scheduler."""
        try:
            # Start bot
            self.logger.info("Starting Telegram bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            await self.send_message("🤖 Bot started and running!-", self.chat_id)
            # Keep running
            await asyncio.Event().wait()
            
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
        finally:
            self.logger.info("Bot stopped")

    def stop(self):
        """Stop the bot and scheduler."""
        self.scheduler.shutdown()
        self.application.stop()
        self.logger.info("Bot stopped manually")
