"""
Generic callback query router
Routes callbacks to appropriate handlers
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main callback query router
    Routes callbacks to appropriate feature handlers
    """
    query = update.callback_query
    data = query.data
    
    logging.info(f"Callback received: {data} from user {query.from_user.id}")
    
    # Route to main menu handler
    if data == "main_menu":
        from handlers.start import main_menu_callback
        return await main_menu_callback(update, context)
    
    # Route to specific feature handlers (will be implemented in Phase 2 & 3)
    if data.startswith("main_menu_"):
        # These will be handled by feature-specific handlers
        await query.answer("This feature will be available soon!")
        return
    
    # Games callbacks (Phase 2)
    if data.startswith("game_"):
        await query.answer("Game features coming in Phase 2!")
        return
    
    # Bank/deposit callbacks (Phase 3)
    if data.startswith("bank_") or data.startswith("deposit_"):
        await query.answer("Banking features coming in Phase 3!")
        return
    
    # Admin callbacks (Phase 3)
    if data.startswith("admin_"):
        await query.answer("Admin features coming in Phase 3!")
        return
    
    # Unknown callback
    logging.warning(f"Unknown callback data: {data}")
    await query.answer("Unknown action")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot"""
    logging.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred while processing your request. "
            "Please try again later."
        )
