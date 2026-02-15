"""
Start command and main menu handlers
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import ContextTypes
    from telegram.constants import ParseMode
else:
    try:
        from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
        from telegram.ext import ContextTypes
        from telegram.constants import ParseMode
    except ImportError:
        pass

from core import initialize_user_data, get_user_data, save_user_data
from utils import get_text, check_banned, check_maintenance
from config import BOT_OWNER_ID, LINK_CHANNEL, LINK_CHAT, LINK_SUPPORT


@check_banned
@check_maintenance
async def start_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /start command - Main entry point"""
    user = update.effective_user
    user_id = user.id
    
    # Initialize user data if new user
    user_data = initialize_user_data(user_id)
    
    # Update user info
    if "userinfo" not in user_data:
        user_data["userinfo"] = {}
    
    user_data["userinfo"]["id"] = user_id
    user_data["userinfo"]["username"] = user.username
    user_data["userinfo"]["first_name"] = user.first_name
    user_data["userinfo"]["last_name"] = user.last_name
    
    save_user_data(user_id)
    
    # Build main menu
    keyboard = [
        [
            InlineKeyboardButton("🎮 Games", callback_data="main_menu_games"),
            InlineKeyboardButton("💰 Balance", callback_data="main_menu_balance")
        ],
        [
            InlineKeyboardButton("🏦 Bank", callback_data="main_menu_bank"),
            InlineKeyboardButton("⚙️ Settings", callback_data="main_menu_settings")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="main_menu_stats"),
            InlineKeyboardButton("❓ Help", callback_data="main_menu_help")
        ]
    ]
    
    # Add community links if available
    if LINK_CHANNEL or LINK_CHAT or LINK_SUPPORT:
        link_row = []
        if LINK_CHANNEL:
            link_row.append(InlineKeyboardButton("📢 Channel", url=LINK_CHANNEL))
        if LINK_CHAT:
            link_row.append(InlineKeyboardButton("💬 Chat", url=LINK_CHAT))
        if LINK_SUPPORT:
            link_row.append(InlineKeyboardButton("🆘 Support", url=LINK_SUPPORT))
        keyboard.append(link_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Welcome message
    welcome_text = (
        f"🎰 <b>Welcome to Telegram Casino Bot!</b> 🎰\n\n"
        f"👋 Hello {user.first_name}!\n\n"
        f"🎲 Experience the thrill of casino games with provably fair outcomes.\n\n"
        f"Choose an option below to get started:"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    
    logging.info(f"User {user_id} ({user.username}) started the bot")


async def main_menu_callback(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle main menu callback - Return to main menu"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Build main menu (same as start command)
    keyboard = [
        [
            InlineKeyboardButton("�� Games", callback_data="main_menu_games"),
            InlineKeyboardButton("💰 Balance", callback_data="main_menu_balance")
        ],
        [
            InlineKeyboardButton("🏦 Bank", callback_data="main_menu_bank"),
            InlineKeyboardButton("⚙️ Settings", callback_data="main_menu_settings")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="main_menu_stats"),
            InlineKeyboardButton("❓ Help", callback_data="main_menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"🎰 <b>Welcome to Telegram Casino Bot!</b> 🎰\n\n"
        f"👋 Hello {user.first_name}!\n\n"
        f"Choose an option below:"
    )
    
    await query.edit_message_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
