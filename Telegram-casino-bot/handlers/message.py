"""
General message handlers
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
else:
    try:
        from telegram import Update
        from telegram.ext import ContextTypes
    except ImportError:
        pass


async def unknown_command_handler(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle unknown commands"""
    await update.message.reply_text(
        "❓ Unknown command. Use /start to see available options."
    )


async def text_message_handler(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle plain text messages (for features like AI chat)"""
    # This will be implemented in later phases
    logging.info(f"Text message from {update.effective_user.id}: {update.message.text}")
