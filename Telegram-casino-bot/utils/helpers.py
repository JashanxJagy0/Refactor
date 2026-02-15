"""
Helper utilities for the bot
Currency conversion, formatting, parsing, and other common functions
"""
from typing import Tuple, Dict, Optional
from config import CURRENCY_RATES, CURRENCY_SYMBOLS
from core.state import user_wallets, user_stats, game_sessions
from core.bot_settings import bot_settings

# Optional PIL import for image processing
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Default language
DEFAULT_LANG = "en"

# ===== CURRENCY CONVERSION =====

def convert_currency(amount_usd: float, to_currency: str = "USD") -> float:
    """Convert amount from USD to target currency"""
    return amount_usd * CURRENCY_RATES.get(to_currency, 1.0)


def convert_to_usd(amount: float, from_currency: str = "USD") -> float:
    """Convert amount from any currency to USD"""
    return amount / CURRENCY_RATES.get(from_currency, 1.0)


def format_currency(amount_usd: float, currency: str = "USD") -> str:
    """Format amount in the specified currency"""
    converted = convert_currency(amount_usd, currency)
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return f"{symbol}{converted:,.2f}"

# ===== AMOUNT PARSING =====

def parse_bet_amount(amount_str: str, user_id: int) -> Tuple[float, float, str]:
    """
    Parse bet amount from user input and convert to USD.
    Returns (amount_in_usd, amount_in_user_currency, user_currency)
    """
    user_currency = get_user_currency(user_id)
    balance_usd = user_wallets.get(user_id, 0.0)
    
    amount_str = amount_str.lower().strip()
    
    if amount_str == 'all':
        amount_usd = balance_usd
        amount_in_currency = convert_currency(balance_usd, user_currency)
    else:
        amount_in_currency = float(amount_str)
        amount_usd = convert_to_usd(amount_in_currency, user_currency)
    
    return amount_usd, amount_in_currency, user_currency

# ===== USERNAME UTILITIES =====

def normalize_username(username: Optional[str]) -> Optional[str]:
    """Normalize username for consistent lookups"""
    if not username:
        return None
    username = username.lower().strip()
    if not username.startswith("@"):
        username = "@" + username
    return username

# ===== BALANCE HELPERS =====

def get_locked_balance_in_games(user_id: int) -> Dict:
    """
    Calculate total locked balance in active games and provide breakdown by game type.
    Returns dict with 'total' and 'games' (list of game details)
    """
    locked_total = 0.0
    game_breakdown = []
    
    for game_id, game in game_sessions.items():
        if game.get('user_id') == user_id and game.get('status') == 'active':
            bet_amount = game.get('bet_amount', 0.0)
            game_type = game.get('game_type', 'unknown')
            locked_total += bet_amount
            game_breakdown.append({
                'game_id': game_id,
                'game_type': game_type,
                'amount': bet_amount
            })
    
    return {'total': locked_total, 'games': game_breakdown}


def format_balance_with_locked(user_id: int, currency: str = "USD") -> str:
    """
    Format balance including locked funds in active games.
    Returns formatted string like "10.50$ + { 5.00$ in game ( mines ) }"
    """
    balance_usd = user_wallets.get(user_id, 0.0)
    formatted_balance = format_currency(balance_usd, currency)
    
    locked_info = get_locked_balance_in_games(user_id)
    
    if locked_info['total'] > 0:
        # Group by game type for cleaner display
        game_totals = {}
        for game in locked_info['games']:
            game_type = game['game_type']
            if game_type not in game_totals:
                game_totals[game_type] = 0.0
            game_totals[game_type] += game['amount']
        
        # Format locked balance display
        locked_parts = []
        for game_type, amount in game_totals.items():
            formatted_locked = format_currency(amount, currency)
            locked_parts.append(f"{formatted_locked} in game ( {game_type} )")
        
        locked_str = " + ".join(locked_parts)
        return f"{formatted_balance} + {{ {locked_str} }}"
    
    return formatted_balance

# ===== USER PREFERENCES =====

def get_user_currency(user_id: int) -> str:
    """Get user's preferred currency"""
    return user_stats.get(user_id, {}).get("userinfo", {}).get("currency", "USD")


def get_user_lang(user_id: int) -> str:
    """Helper function to get user's language preference"""
    return user_stats.get(user_id, {}).get("userinfo", {}).get("language", DEFAULT_LANG)

# ===== MENU OWNERSHIP =====

def check_menu_ownership(query, context) -> bool:
    """
    Check if the user clicking the button is the owner of the menu.
    For group chats, we track menu ownership by message_id.
    Returns True if the user is the owner or if no owner is set.
    Returns False if another user is trying to interact with the menu.
    """
    if 'menu_owners' not in bot_settings:
        bot_settings['menu_owners'] = {}
    
    message_id = query.message.message_id
    chat_id = query.message.chat_id
    menu_key = f"{chat_id}_{message_id}"
    
    menu_owner_id = bot_settings['menu_owners'].get(menu_key)
    if menu_owner_id and query.from_user.id != menu_owner_id:
        return False
    return True


def set_menu_owner(message, user_id: int):
    """
    Set the owner of a menu message.
    Should be called after sending a message with inline keyboard.
    """
    if 'menu_owners' not in bot_settings:
        bot_settings['menu_owners'] = {}
    
    menu_key = f"{message.chat_id}_{message.message_id}"
    bot_settings['menu_owners'][menu_key] = user_id
    
    # Clean up old entries (keep only last 1000 to prevent memory issues)
    if len(bot_settings['menu_owners']) > 1000:
        keys_to_remove = list(bot_settings['menu_owners'].keys())[:100]
        for key in keys_to_remove:
            del bot_settings['menu_owners'][key]

# ===== IMAGE PROCESSING =====

def create_circular_mask(image_size: Tuple[int, int]):
    """Create a circular mask for profile pictures"""
    if not PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is required for image processing")
    
    mask = Image.new('L', image_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, image_size[0], image_size[1]), fill=255)
    return mask
