"""
Game command and callback handlers
Routes game-related commands and callbacks to appropriate game implementations
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

from features.games.registry import game_registry
from utils.decorators import check_banned, check_maintenance


@check_banned
@check_maintenance
async def mines_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /mines command"""
    from features.games.house_games.mines import mines_game
    
    # Get parameters
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /mines <bet_amount> [num_mines]\n"
            "Example: /mines 1.50 5\n"
            "Default mines: 3"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        num_mines = int(context.args[1]) if len(context.args) > 1 else 3
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount or number of mines")
        return
    
    await mines_game.start_game(update, context, bet_amount, num_mines)


@check_banned
@check_maintenance
async def coinflip_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /flip command"""
    from features.games.house_games.coinflip import coinflip_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /flip <bet_amount>\n"
            "Example: /flip 1.50"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await coinflip_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def diceroll_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /dice command"""
    from features.games.house_games.diceroll import diceroll_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /dice <bet_amount> [prediction]\n"
            "Example: /dice 1.50 6\n"
            "Default prediction: 6"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        prediction = int(context.args[1]) if len(context.args) > 1 else 6
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount or prediction")
        return
    
    await diceroll_game.start_game(update, context, bet_amount, prediction)


@check_banned
@check_maintenance
async def tower_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /tower command"""
    from features.games.house_games.tower import tower_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /tower <bet_amount> [difficulty]\n"
            "Difficulty: easy, medium (default), hard\n"
            "Example: /tower 1.50 hard"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        difficulty = context.args[1] if len(context.args) > 1 else 'medium'
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await tower_game.start_game(update, context, bet_amount, difficulty)


@check_banned
@check_maintenance
async def roulette_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /roulette command"""
    from features.games.house_games.roulette import roulette_game
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /roulette <bet_amount> <bet_type> [number]\n"
            "Bet types: single (0-36), red, black, even, odd, low, high\n"
            "Example: /roulette 1.50 red\n"
            "Example: /roulette 1.50 single 17"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        bet_type = context.args[1].lower()
        bet_value = int(context.args[2]) if len(context.args) > 2 else None
    except ValueError:
        await update.message.reply_text("❌ Invalid parameters")
        return
    
    await roulette_game.start_game(update, context, bet_amount, bet_type, bet_value)


@check_banned
@check_maintenance
async def slots_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /slots command"""
    from features.games.house_games.slots import slots_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /slots <bet_amount>\n"
            "Example: /slots 1.50"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await slots_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def keno_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /keno command"""
    from features.games.house_games.keno import keno_game
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /keno <bet_amount> <numbers...>\n"
            "Pick 1-8 numbers (1-80)\n"
            "Example: /keno 1.50 5 12 23 45 67"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        numbers = [int(n) for n in context.args[1:]]
    except ValueError:
        await update.message.reply_text("❌ Invalid parameters")
        return
    
    await keno_game.start_game(update, context, bet_amount, numbers)


async def game_callback_router(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Route game callbacks to appropriate game handlers"""
    query = update.callback_query
    data = query.data
    
    # Route based on callback data prefix
    if data.startswith("mines_"):
        from features.games.house_games.mines import mines_game
        await mines_game.handle_callback(update, context)
    elif data.startswith("flip_"):
        from features.games.house_games.coinflip import coinflip_game
        await coinflip_game.handle_callback(update, context)
    elif data.startswith("tower_"):
        from features.games.house_games.tower import tower_game
        await tower_game.handle_callback(update, context)
    # Add more game routing as games are implemented
    else:
        await query.answer("Unknown game action")


@check_banned
@check_maintenance
async def emoji_darts_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /edarts command"""
    from features.games.emoji_games.single_emoji import darts_single_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /edarts <bet_amount>\nExample: /edarts 1.50")
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await darts_single_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def emoji_soccer_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /esoccer command"""
    from features.games.emoji_games.single_emoji import soccer_single_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /esoccer <bet_amount>\nExample: /esoccer 1.50")
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await soccer_single_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def emoji_basketball_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /ebasket command"""
    from features.games.emoji_games.single_emoji import basketball_single_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /ebasket <bet_amount>\nExample: /ebasket 1.50")
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await basketball_single_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def emoji_bowling_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /ebowl command"""
    from features.games.emoji_games.single_emoji import bowling_single_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /ebowl <bet_amount>\nExample: /ebowl 1.50")
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await bowling_single_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def emoji_slot_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /eslot command"""
    from features.games.emoji_games.single_emoji import slot_single_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /eslot <bet_amount>\nExample: /eslot 1.50")
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await slot_single_game.start_game(update, context, bet_amount)


# Command handlers mapping for easy registration
GAME_COMMAND_HANDLERS = {
    "mines": mines_command,
    "m": mines_command,  # Alias
    "flip": coinflip_command,
    "coinflip": coinflip_command,
    "dice": diceroll_command,
    "d": diceroll_command,  # Alias
    "tower": tower_command,
    "tw": tower_command,  # Alias
    "roulette": roulette_command,
    "ru": roulette_command,  # Alias
    "slots": slots_command,
    "sl": slots_command,  # Alias
    "keno": keno_command,
    "k": keno_command,  # Alias
    "edarts": emoji_darts_command,
    "esoccer": emoji_soccer_command,
    "ebasket": emoji_basketball_command,
    "ebowl": emoji_bowling_command,
    "eslot": emoji_slot_command,
}
