"""
Main entry point for the Telegram Casino Bot
Refactored modular architecture for better maintainability
"""
import logging
import atexit
import warnings
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Suppress warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*CallbackQueryHandler.*')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import configuration
from config import BOT_TOKEN, BOT_OWNER_ID

# Import core modules
from core import (
    create_directories, load_bot_state, save_bot_state,
    user_wallets, user_stats
)

# Import utilities
from utils import load_language_files

# Import handlers
from handlers import (
    start_command, callback_query_handler, error_handler,
    unknown_command_handler
)


def initialize_bot():
    """Initialize bot data and directories"""
    logger.info("Initializing bot...")
    
    # Create necessary directories
    create_directories()
    
    # Load language files
    logger.info("Loading language files...")
    load_language_files()
    
    # Load bot state from disk
    logger.info("Loading bot state...")
    load_bot_state()
    
    logger.info(f"Loaded {len(user_stats)} users and {len(user_wallets)} wallets")
    logger.info("Bot initialization complete!")


def register_handlers(application: Application):
    """Register all command and callback handlers"""
    logger.info("Registering handlers...")
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Game command handlers (Phase 2)
    from features.games.handlers import GAME_COMMAND_HANDLERS
    for command, handler in GAME_COMMAND_HANDLERS.items():
        application.add_handler(CommandHandler(command, handler))
    
    # Callback query handler (routes to specific handlers)
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Unknown command handler (must be last)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("Handlers registered successfully!")


def main():
    """Main function to start the bot"""
    logger.info("=" * 60)
    logger.info("Starting Telegram Casino Bot (Refactored)")
    logger.info("=" * 60)
    
    # Initialize bot
    initialize_bot()
    
    # Register save function to be called on exit
    atexit.register(save_bot_state)
    
    # Create application
    logger.info("Creating application...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    register_handlers(application)
    
    # Start the bot
    logger.info("Starting bot polling...")
    logger.info(f"Bot owner ID: {BOT_OWNER_ID}")
    logger.info("Bot is now running! Press Ctrl+C to stop.")
    
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down...")
        save_bot_state()
        logger.info("Bot shutdown complete!")


if __name__ == "__main__":
    main()
