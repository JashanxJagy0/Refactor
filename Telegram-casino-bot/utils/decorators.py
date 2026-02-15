"""
Decorators for command handlers
Provides security and validation checks
"""
from __future__ import annotations
import functools
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

from core.state import user_stats
from core.bot_settings import is_maintenance_mode
from config import BOT_OWNER_ID


def check_banned(func):
    """Decorator to check if user is banned before executing command"""
    @functools.wraps(func)
    async def wrapper(update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check if user is banned
        if user_id in user_stats and user_stats[user_id].get("banned", False):
            await update.message.reply_text(
                "❌ You are banned from using this bot.\n"
                "If you believe this is an error, please contact support."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def check_maintenance(func):
    """Decorator to check if bot is in maintenance mode"""
    @functools.wraps(func)
    async def wrapper(update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        user_id = update.effective_user.id
        
        # Allow owner to use bot during maintenance
        if is_maintenance_mode() and user_id != BOT_OWNER_ID:
            await update.message.reply_text(
                "🔧 Bot is currently under maintenance.\n"
                "Please try again later."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def admin_only(func):
    """Decorator to restrict command to bot owner only"""
    @functools.wraps(func)
    async def wrapper(update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id != BOT_OWNER_ID:
            await update.message.reply_text(
                "❌ This command is restricted to bot administrators only."
            )
            logging.warning(f"Unauthorized admin access attempt by user {user_id}")
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def private_chat_only(func):
    """Decorator to restrict command to private chats only"""
    @functools.wraps(func)
    async def wrapper(update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        if update.effective_chat.type != "private":
            await update.message.reply_text(
                "❌ This command can only be used in private chat with the bot."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def group_chat_only(func):
    """Decorator to restrict command to group chats only"""
    @functools.wraps(func)
    async def wrapper(update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "❌ This command can only be used in group chats."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper
