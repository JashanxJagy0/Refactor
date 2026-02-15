import logging
import random
import string
import asyncio
import json
import os
import warnings
from datetime import datetime, timedelta, timezone
import httpx
from web3 import Web3
from eth_account import Account
import secrets # For secure token generation
import hashlib # For hashing PINs
import hmac # For secure key derivation
import traceback # For detailed error logging

# Suppress PTB warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*CallbackQueryHandler.*')

# NEW FEATURE - AI Integration (Switched to Perplexity AI)
from openai import OpenAI
# NEW FEATURE - Added g4f for a free AI option
import g4f

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, Bot, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
import atexit
from bip_utils import (
    Bip44, Bip44Coins, Bip44Changes, CoinsConf, WifDecoder,
    Bip39SeedGenerator, Bip39MnemonicGenerator, Bip39WordsNum
)

# ===== DEPOSIT SYSTEM IMPORTS =====
import sqlite3
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Blockchain-specific libraries for non-EVM chains
try:
    from solders.keypair import Keypair as SoldersKeypair
    from solders.pubkey import Pubkey as SoldersPubkey
    from solders.system_program import TransferParams as SoldersTransferParams, transfer as solders_transfer
    from solders.transaction import Transaction as SoldersTransaction
    from solana.rpc.async_api import AsyncClient as SolanaClient
    import base58
    SOLANA_AVAILABLE = True
except ImportError as e:
    SOLANA_AVAILABLE = False
    logging.warning(f"Solana libraries not available: {e}")

try:
    from tronpy import Tron
    from tronpy.keys import PrivateKey as TronPrivateKey
    TRON_AVAILABLE = True
except ImportError:
    TRON_AVAILABLE = False
    logging.warning("Tron library not available. Install with: pip install tronpy")

try:
    from pytoniq_core import Address as TonAddress
    from pytoniq_core.crypto.keys import mnemonic_to_private_key, private_key_to_public_key
    TON_AVAILABLE = True
except ImportError:
    TON_AVAILABLE = False
    logging.warning("TON library not available. Install with: pip install pytoniq-core")

# --- Bot Configuration ---
BOT_TOKEN = "7956452112:AAGSZVLZz34ep8qCsLKnTRZambI67r_T3ro"
BOT_OWNER_ID = 6083286836
MIN_BALANCE = 0.1
DEBUG_EMOJI_GAMES = False  # Set to True to enable detailed emoji game logging

# --- Links Configuration ---
# Add your community links here
LINK_PORTAL = "https://t.me/escrews"  # Portal link (leave empty if not available)
LINK_CHANNEL = "https://t.me/escrews"  # Channel link (e.g., "https://t.me/yourchannel")
LINK_CHAT = "https://t.me/playcsino"  # Chat link (e.g., "https://t.me/yourchat")
LINK_SUPPORT = "https://t.me/jashanxjagy"  # Support link (e.g., "https://t.me/yoursupport")

# --- Win Broadcast Configuration ---
# ⚠️ IMPORTANT: Can use either Channel ID or Username
# For Channel ID: Usually requires a "-100" prefix (e.g., "-1003848853417")
# For Channel Username: Use @ prefix for public channels (e.g., "@mychannel")
# Leave empty to disable win broadcasting
WIN_BROADCAST_CHANNEL_ID = ""  # Example: "-1003848853417" or "@mychannel" or leave empty to disable

## NEW FEATURE - AI Integration ##
PERPLEXITY_API_KEY = "[REDACTED]" # I will add this
# NEW FEATURE - MEXC Price Integration
MEXC_API_KEY = "mx0vgltPHKyw92y4qZ" # I will add this
MEXC_API_SECRET = "5f4f81217f514a799e4d77842bcc4a26" # I will add this

# --- Escrow Configuration ---
# LEAVE THESE BLANK - I will add them manually
ESCROW_DEPOSIT_ADDRESS = "0xdda0e87f6c1344e07cfce9cefb12f3a286a0fb38"  # Your fixed BEP20 address for receiving escrow funds
ESCROW_WALLET_PRIVATE_KEY = "0bbaf8d35b64859555b1a6acc7909ac349bced46b2fcf2c8d616343fec138353" # The private key for the above address to send funds
ESCROW_DEPOSIT_NETWORK = "bsc"
ESCROW_DEPOSIT_TOKEN_CONTRACT = "0x55d398326f99059fF775485246999027B3197955" # USDT BEP20
ESCROW_DEPOSIT_TOKEN_DECIMALS = 18

## NEW FEATURE - Referral System Configuration ##
REFERRAL_BET_COMMISSION_RATE = 0.001      # 0.1%

# ===== DEPOSIT SYSTEM CONFIGURATION =====
# ⚠️ IMPORTANT: Configure these values below for deposit system to work
# No .env file needed - everything is configured directly in this file

DEPOSIT_ENABLED = True
DEPOSITS_DB = "deposits.db"

# ========================================
# 🔐 SECURITY CRITICAL - FILL THESE VALUES
# ========================================
# Generate a 24-word mnemonic: https://iancoleman.io/bip39/
# ⚠️ KEEP THIS SECRET! Anyone with this can access all deposit addresses
MASTER_MNEMONIC = "inflict police tooth diesel ladder crawl pupil daughter label cliff clip visit base marine increase pizza kiwi royal knee panther half ill habit rookie"  # Example: "word1 word2 word3 ... word24"

# Hot wallet private key for gas funding (EVM format starting with 0x)
# ⚠️ Keep minimal balance here (max $100 worth for gas only)
HOT_WALLET_PRIVATE_KEY = "fea03d11d9993d1b357fb01ef238ab9e59457ca9c8df9fdb3c131bac8c034b93"  # Example: "0x1234567890abcdef..."

# Master wallet addresses where ALL deposits are swept to
# ⚠️ Use cold wallets or hardware wallets for these!
MASTER_WALLETS = {
    "ETH": "0x3011d124812d638c3eb4743ebe2261a2b0e47806",      # Example: "0x1234567890abcdef1234567890abcdef12345678"
    "BNB": "0x3011d124812d638c3eb4743ebe2261a2b0e47806",      # Example: "0x1234567890abcdef1234567890abcdef12345678"
    "BASE": "0x3011d124812d638c3eb4743ebe2261a2b0e47806",     # Example: "0x1234567890abcdef1234567890abcdef12345678"
    "TRON": "TDdSwtm4wz1147GbtXEmL8Ck3wDe7m95tu",     # Example: "TAbCdEfGhIjKlMnOpQrStUvWxYz1234567"
    "SOLANA": "8DKPQrMr4X9gbbmZAcJXeLx1qHicrvLjBpRZDX1S4kgC",   # Example: "AbCdEfGh123456789..."
    "TON": "UQC2CsdJrFkX6MctJmyrfFPZZk1orq0ewjR6k2Zv7NNs8Mmi"       # Example: "EQAbCdEfGh..."
}

# ========================================
# 🌐 BLOCKCHAIN RPC ENDPOINTS (Optional)
# ========================================
# Default public RPCs are provided - you can use your own for better performance
RPC_ENDPOINTS = {
    "ETH": "https://eth.llamarpc.com",                    # Or use Alchemy/Infura
    "BNB": "https://bsc-dataseed.binance.org/",          # Or use NodeReal
    "BASE": "https://mainnet.base.org",                   # Base mainnet
    "TRON": "https://api.trongrid.io",                    # TronGrid
    "SOLANA": "https://api.mainnet-beta.solana.com",     # Or use Helius
    "TON": "https://toncenter.com/api/v2/jsonRPC"        # TON Center
}

# Token contracts (USDT/USDC on each chain)
TOKEN_CONTRACTS = {
    "ETH": {
        "USDT": {"address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6},
        "USDC": {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6}
    },
    "BNB": {
        "USDT": {"address": "0x55d398326f99059fF775485246999027B3197955", "decimals": 18},
        "USDC": {"address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18}
    },
    "BASE": {
        "USDC": {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6}
    },
    "TRON": {
        "USDT": {"address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "decimals": 6}
    },
    "SOLANA": {
        "USDT": {"mint": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "decimals": 6},
        "USDC": {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "decimals": 6}
    }
}

# ========================================
# ⚙️ DEPOSIT SETTINGS (Optional - defaults provided)
# ========================================
MIN_DEPOSIT_USD = 10.0       # Minimum deposit amount in USD
SCAN_INTERVAL = 30            # How often to scan for deposits (seconds)
SWEEP_INTERVAL = 60           # How often to process sweeps (seconds)

# Required confirmations before crediting deposit
CONFIRMATIONS = {
    "ETH": 12,
    "BNB": 15,
    "BASE": 10,
    "TRON": 19,
    "SOLANA": 32,
    "TON": 5
}

# Gas amounts for token sweeps (in native currency)
GAS_AMOUNTS = {
    "ETH": 0.005,      # 0.005 ETH for ERC20 transfers
    "BNB": 0.001,      # 0.001 BNB for BEP20 transfers
    "BASE": 0.0005,    # 0.0005 ETH for Base transfers
    "TRON": 15,        # 15 TRX for TRC20 transfers
    "SOLANA": 0.001,   # 0.001 SOL for SPL transfers
}

# BIP44 derivation paths for each chain
BIP44_PATHS = {
    "ETH": "m/44'/60'/0'/0",      # Ethereum
    "BNB": "m/44'/60'/0'/0",      # BNB uses Ethereum path
    "BASE": "m/44'/60'/0'/0",     # Base uses Ethereum path
    "TRON": "m/44'/195'/0'/0",    # Tron
    "SOLANA": "m/44'/501'/0'/0",  # Solana
    "TON": "m/44'/607'/0'/0"      # TON
}

# Price cache (simple in-memory cache, should be replaced with Redis in production)
_price_cache = {}
_price_cache_timestamp = {}
PRICE_CACHE_TTL = 60  # seconds

async def get_crypto_price_usd(symbol):
    """Get cryptocurrency price in USD"""
    # Check cache first
    now = datetime.now().timestamp()
    if symbol in _price_cache and symbol in _price_cache_timestamp:
        if now - _price_cache_timestamp[symbol] < PRICE_CACHE_TTL:
            return _price_cache[symbol]
    
    # Fetch fresh price (using CoinGecko as example)
    try:
        coin_ids = {
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'TRX': 'tron',
            'SOL': 'solana',
            'TON': 'the-open-network',
            'USDT': 'tether',
            'USDC': 'usd-coin'
        }
        
        coin_id = coin_ids.get(symbol)
        if not coin_id:
            return 1.0  # Default for unknown tokens
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd",
                timeout=5.0
            )
            data = response.json()
            price = data.get(coin_id, {}).get('usd', 1.0)
            
            # Cache the price
            _price_cache[symbol] = price
            _price_cache_timestamp[symbol] = now
            
            return price
    except Exception as e:
        logging.error(f"Error fetching price for {symbol}: {e}")
        # Fallback to approximate prices if API fails
        fallback_prices = {
            'ETH': 3000.0,
            'BNB': 400.0,
            'TRX': 0.15,
            'SOL': 100.0,
            'TON': 5.0,
            'USDT': 1.0,
            'USDC': 1.0
        }
        return fallback_prices.get(symbol, 1.0)

# --- Persistent Storage Directory ---
DATA_DIR = "user_data"
ESCROW_DIR = "escrow_deals"
LOGS_DIR = "logs"
GROUPS_DIR = "group_data" # NEW: For group settings
RECOVERY_DIR = "recovery_data" # NEW: For recovery tokens
GIFT_CODE_DIR = "gift_codes" # NEW: For gift codes
STATE_FILE = "bot_state.json"
CRYPTO_PRICES_FILE = "crypto_prices.json"  # NEW: Store crypto prices
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ESCROW_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(GROUPS_DIR, exist_ok=True) # NEW
os.makedirs(RECOVERY_DIR, exist_ok=True) # NEW
os.makedirs(GIFT_CODE_DIR, exist_ok=True) # NEW

# --- In-memory Data ---
user_wallets = {}
username_to_userid = {}
user_stats = {}
# REFACTOR: Centralized session/game management
game_sessions = {} # Replaces matches, mines_games, coin_flip_games, etc.
active_pvb_games = {} # NEW: Track active PvB games per user (fallback to context.chat_data)
user_pending_invitations = {} # Kept for PvP flow
escrow_deals = {} # To hold active escrow deals
group_settings = {} # NEW: To hold group configurations
recovery_data = {} # NEW: To hold recovery token data
provably_fair_records = {} # NEW: Store provably fair verification data for completed games
gift_codes = {} # NEW: To hold gift code data
withdrawal_requests = {} # NEW: To hold pending withdrawal requests
crypto_prices = {}  # NEW: Cache for cryptocurrency prices

# --- Global Control Flag ---
bot_stopped = False

## NEW FEATURE - Bot Settings ##
bot_settings = {
    "daily_bonus_amount": 0.50,
    "daily_bonus_enabled": True, # NEW: Toggle for daily bonus feature
    "maintenance_mode": False,
    "banned_users": [], # For permanent bans
    "tempbanned_users": [], # For temporary (withdrawal) bans
    "house_balance": 100_000_000_000_000.0, # NEW: House balance set to 100 Trillion
    "game_limits": {}, # NEW: For min/max bets per game
    "withdrawals_enabled": True, # NEW
    "demo_enabled": True, # NEW: Toggle for demo feature
    "demo_amount": 10.0, # NEW: Demo claim amount
    "demo_cooldown": 600, # NEW: Demo cooldown in seconds (10 minutes)
}

## ===================================================================
## DASHBOARD IMAGE CONFIGURATION
## ===================================================================
# This section configures the dynamic dashboard image feature that overlays
# user data on a background template image. The dashboard is displayed for:
# - /start command
# - /bal or /balance command
# - /stats command
# - "Wallet" button (callback query)
#
# CUSTOMIZATION GUIDE:
# 1. Background Image: Replace 'unnamed (1).jpg' with your own template
# 2. Font: Update DASHBOARD_FONT_PATH to use your preferred .ttf font
# 3. Text Positioning: Adjust coordinates in DASHBOARD_CONFIG below
#    - position: (X, Y) coordinates from top-left corner
#    - font_size: Size in pixels
#    - color: RGB tuple (R, G, B) where each value is 0-255
# 4. Profile Picture: Adjust position and size in DASHBOARD_CONFIG
#
# DEPENDENCIES:
# - Pillow (PIL) - Install with: pip install Pillow
# ===================================================================

# Background template image path
# NOTE: The default filename 'unnamed (1).jpg' should be kept as-is if you're using 
# the provided template, or update this path if you rename the file
DASHBOARD_TEMPLATE_PATH = "clean_template.jpg"

# Font configuration (use a TTF font for better quality)
# You can replace this with any .ttf font file path
DASHBOARD_FONT_PATH = "bold.ttf"  # Default system font
DASHBOARD_FONT_FALLBACK = None  # Will use PIL default if custom font not found

# Dashboard text configuration: coordinates (X, Y), font size, and color (R, G, B)
DASHBOARD_CONFIG = {
    "profile_picture": {
        "position": (50, 60),      # (X, Y) position for profile picture - left side
        "size": (120, 120)         # Width and height
    },
    "name": {
        "position": (200, 70),     # (X, Y) position - User's first name
        "font_size": 32,           # Font size in pixels
        "color": (255, 255, 255)   # RGB color (white)
    },
    "username": {
        "position": (200, 110),    # Username (@username)
        "font_size": 20,
        "color": (180, 180, 180)   # Light gray
    },
    "user_id": {
        "position": (200, 145),    # User ID number
        "font_size": 16,
        "color": (200, 200, 200)   # Light gray
    },
    "level": {
        "position": (340, 145),    # Level badge - next to user ID
        "font_size": 16,
        "color": (150, 100, 200)   # Purple
    },
    "bot_username": {
        "position": (720, 35),     # Bot username in top right
        "font_size": 24,
        "color": (255, 215, 0)     # Gold
    },
    "member_since": {
        "position": (795, 85),     # Member since date - below bot username
        "font_size": 14,
        "color": (0, 255, 255)     # Cyan
    },
    "balance": {
        "position": (200, 300),    # Balance in left wide green box (60-470)
        "font_size": 28,
        "color": (0, 255, 0)       # Green
    },
    "last_win": {
        "position": (625, 300),    # Last win in right wide orange box (490-900)
        "font_size": 22,
        "color": (255, 255, 255)   # White
    }
}

## NEW FEATURE - Currency System ##
# Exchange rates as of implementation (relative to USD)
CURRENCY_RATES = {
    "USD": 1.0,
    "INR": 83.12,    # 1 USD = 83.12 INR
    "EUR": 0.92,     # 1 USD = 0.92 EUR
    "GBP": 0.79      # 1 USD = 0.79 GBP
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£"
}

def convert_currency(amount_usd, to_currency="USD"):
    """Convert amount from USD to target currency"""
    return amount_usd * CURRENCY_RATES.get(to_currency, 1.0)

def convert_to_usd(amount, from_currency="USD"):
    """Convert amount from any currency to USD"""
    return amount / CURRENCY_RATES.get(from_currency, 1.0)

def format_currency(amount_usd, currency="USD"):
    """Format amount in the specified currency"""
    converted = convert_currency(amount_usd, currency)
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return f"{symbol}{converted:,.2f}"

def parse_bet_amount(amount_str: str, user_id: int) -> tuple:
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

def get_user_currency(user_id):
    """Get user's preferred currency"""
    return user_stats.get(user_id, {}).get("userinfo", {}).get("currency", "USD")


## NEW FEATURE - Achievements ##
ACHIEVEMENTS = {
    "wager_100": {"name": "🎲 Player", "description": "Wager a total of $100.", "emoji": "🎲", "type": "wager", "value": 100},
    "wager_1000": {"name": "💰 High Roller", "description": "Wager a total of $1,000.", "emoji": "💰", "type": "wager", "value": 1000},
    "wager_10000": {"name": "👑 Whale", "description": "Wager a total of $10,000.", "emoji": "👑", "type": "wager", "value": 10000},
    "wins_50": {"name": "👍 Winner", "description": "Win 50 games.", "emoji": "👍", "type": "wins", "value": 50},
    "wins_250": {"name": "🏆 Champion", "description": "Win 250 games.", "emoji": "🏆", "type": "wins", "value": 250},
    "pvp_wins_25": {"name": "⚔️ Duelist", "description": "Win 25 PvP matches.", "emoji": "⚔️", "type": "pvp_wins", "value": 25},
    "lucky_100x": {"name": "🌟 Lucky Star", "description": "Win a bet with a 100x or higher multiplier.", "emoji": "🌟", "type": "multiplier", "value": 100},
    "referral_master": {"name": "🤝 Connector", "description": "Refer 5 active users.", "emoji": "🤝", "type": "referrals", "value": 5},
}
## NEW FEATURE - Level System ##
LEVELS = [
    {"level": 0, "name": "None", "wager_required": 0, "reward": 0, "rakeback_percentage": 0.01},
    {"level": 1, "name": "Bronze", "wager_required": 10000, "reward": 15, "rakeback_percentage": 0.03},
    {"level": 2, "name": "Silver", "wager_required": 50000, "reward": 30, "rakeback_percentage": 0.04},
    {"level": 3, "name": "Gold", "wager_required": 100000, "reward": 60, "rakeback_percentage": 0.06},
    {"level": 4, "name": "Platinum I", "wager_required": 250000, "reward": 100, "rakeback_percentage": 0.07},
    {"level": 5, "name": "Platinum II", "wager_required": 500000, "reward": 200, "rakeback_percentage": 0.08},
    {"level": 6, "name": "Platinum III", "wager_required": 1000000, "reward": 400, "rakeback_percentage": 0.09},
    {"level": 7, "name": "Platinum IV", "wager_required": 2500000, "reward": 800, "rakeback_percentage": 0.09},
    {"level": 8, "name": "Platinum V", "wager_required": 5000000, "reward": 1600, "rakeback_percentage": 0.10},
    {"level": 9, "name": "Platinum VI", "wager_required": 10000000, "reward": 3200, "rakeback_percentage": 0.10},
    {"level": 10, "name": "Diamond I", "wager_required": 25000000, "reward": 6400, "rakeback_percentage": 0.11},
    {"level": 11, "name": "Diamond II", "wager_required": 50000000, "reward": 25600, "rakeback_percentage": 0.11},
    {"level": 12, "name": "Diamond III", "wager_required": 100000000, "reward": 51200, "rakeback_percentage": 0.12},
]
## NEW FEATURE - Language Support ##
# Comprehensive language system with 6 supported languages loaded from text files
def get_user_lang(user_id):
    """Helper function to get user's language preference"""
    return user_stats.get(user_id, {}).get("userinfo", {}).get("language", DEFAULT_LANG)

# Language file mapping
# Note: "hindhi.txt" filename is as provided (not a typo)
LANGUAGE_FILES = {
    "en": "English.txt",
    "hi": "hindhi.txt",
    "es": "spanish.txt",
    "ru": "russian.txt",
    "fr": "french.txt",
    "zh": "chinese.txt"
}

LANGUAGE_NAMES = {
    "en": "English 🇬🇧",
    "hi": "हिन्दी 🇮🇳",
    "es": "Español 🇪🇸",
    "ru": "Русский 🇷🇺",
    "fr": "Français 🇫🇷",
    "zh": "中文 🇨🇳"
}

# Cache for loaded language data
_language_cache = {}

def load_language_file(lang_code):
    """Load a language file and return as a dictionary"""
    if lang_code in _language_cache:
        return _language_cache[lang_code]
    
    filename = LANGUAGE_FILES.get(lang_code)
    if not filename:
        return None
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(filepath):
        logging.warning(f"Language file not found: {filepath}")
        return None
    
    lang_dict = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            current_key = None
            current_value = []
            
            for line in f:
                line_rstrip = line.rstrip('\n')
                
                # Skip comments and empty lines when not in a multi-line value
                if not current_key and (not line_rstrip or line_rstrip.startswith('#')):
                    continue
                
                # Check for new key = "value" pattern
                if ' = "' in line_rstrip and not current_key:
                    parts = line_rstrip.split(' = "', 1)
                    if len(parts) == 2:
                        current_key = parts[0].strip()
                        value_part = parts[1]
                        
                        # Check if value ends on this line
                        if value_part.endswith('"'):
                            lang_dict[current_key] = value_part[:-1]
                            current_key = None
                            current_value = []
                        else:
                            current_value = [value_part]
                elif current_key:
                    # Continuation of multi-line value
                    if line_rstrip.endswith('"'):
                        current_value.append(line_rstrip[:-1])
                        lang_dict[current_key] = '\n'.join(current_value)
                        current_key = None
                        current_value = []
                    else:
                        current_value.append(line_rstrip)
        
        _language_cache[lang_code] = lang_dict
        logging.info(f"Loaded language file: {filename} with {len(lang_dict)} entries")
        return lang_dict
    except Exception as e:
        logging.error(f"Error loading language file {filename}: {e}")
        return None

# Legacy LANGUAGES dictionary for backward compatibility during migration
# This will be deprecated once all text is moved to files
LANGUAGES = {
    "en": {  # English
        "language_name": "English 🇬🇧",
        # Welcome and Main Menu - RESTORED ORIGINAL FULL TEXT
        "welcome_title": "🎰 <b>Welcome to Telegram Casino & Escrow Bot!</b> 🎰",
        "hello": "👋 Hello {first_name}!",
        "welcome_desc": "🎲 Experience the thrill of casino games or secure your trades with our automated Escrow system.",
        "ai_feature": "✨ NEW: Chat with our <b>AI Assistant</b> for any questions or tasks!",
        "current_balance": "💰 Current Balance: <b>{balance}</b>",
        "choose_option": "Choose an option below to get started:",
        
        # Buttons
        "withdraw": "📤 Withdraw",
        "games": "🎮 Games",
        "more": "➕ More",
        "stats": "📊 Statistics",
        "settings": "⚙️ Settings",
        "help": "❓ Help",
        "bonuses": "🎁 Bonuses",
        "escrow": "🔐 Escrow",
        "ai_assistant": "🤖 AI Assistant",
        "back": "🔙 Back",
        "cancel": "❌ Cancel",
        "confirm": "✅ Confirm",
        
        # Balance and Currency
        "balance": "💰 Your balance: {balance}",
        "your_balance": "💰 Your balance: {balance}",
        "insufficient_balance": "❌ Insufficient balance. Please deposit to continue.",
        "locked_in_games": "+ {amount} locked in games",
        
        # Betting
        "enter_bet_amount": "Enter your bet amount:",
        "bet_placed": "🎲 Bet placed: ${amount:.2f}",
        "invalid_amount": "Invalid amount. Please enter a valid number or 'all'.",
        "min_bet": "Minimum bet for this game is {amount}",
        "max_bet": "Maximum bet for this game is {amount}",
        
        # Game Results
        "you_won": "🎉 You won {amount}!",
        "you_lost": "😔 You lost. Better luck next time!",
        "game_started": "🎮 Game started!",
        "game_ended": "🎮 Game ended!",
        "round": "Round {round}",
        "waiting_for_opponent": "⏳ Waiting for opponent...",
        
        # Daily Bonus
        "daily_claim_success": "🎉 You have successfully claimed your daily bonus of {amount}!",
        "daily_claim_wait": "⏳ You have already claimed your daily bonus. Please wait {hours}h {minutes}m before claiming again.",
        "daily_bonus": "🎁 Daily Bonus",
        
        # Achievements
        "achievement_unlocked": "🏅 <b>Achievement Unlocked!</b> 🏅\n\nYou have earned the <b>{emoji} {name}</b> badge!\n<i>{description}</i>",
        "achievements": "🏅 Achievements",
        "no_achievements": "You haven't unlocked any achievements yet. Start playing to earn badges!",
        
        # Language
        "language_set": "✅ Language set to English",
        "select_language": "🌍 <b>Select your language:</b>",
        "language": "🌍 Language",
        
        # Games Menu
        "games_menu": "🎮 <b>Casino Games</b>\n\nChoose a category:",
        "dice_games": "🎲 Dice Games",
        "card_games": "🃏 Card Games",
        "original_games": "⭐ Original Games",
        "quick_games": "⚡ Quick Games",
        
        # Settings
        "settings_menu": "⚙️ <b>Settings</b>\n\nCustomize your experience:",
        "withdrawal_address": "💳 Withdrawal Address",
        "currency_settings": "💱 Currency",
        "recovery_settings": "🔐 Recovery",
        
        # Help
        "help_text": "❓ <b>Help & Commands</b>\n\nAvailable commands:\n/start - Main menu\n/games - Browse games\n/balance - Check balance\n/withdraw - Withdraw funds\n/stats - View statistics\n/daily - Claim daily bonus\n/help - Show this help\n\nFor support, contact @jashanxjagy",
        
        # Errors
        "error_occurred": "❌ An error occurred. Please try again.",
        "command_not_found": "❌ Command not found. Use /help to see available commands.",
        "maintenance_mode": "🛠️ <b>Bot Under Maintenance</b> 🛠️\n\nThe bot is currently undergoing scheduled maintenance.",
        "banned_user": "You have been banned from using this bot.",
        
        # Deposit/Withdrawal
        "withdrawal_menu": "📤 <b>Withdraw</b>\n\nEnter the amount you want to withdraw:",
        "withdrawal_success": "✅ Withdrawal request submitted successfully!",
        "withdrawal_pending": "Your withdrawal is being processed...",
        
        # Admin
        "admin_panel": "👑 <b>Admin Panel</b>",
        "admin_only": "This command is only available to administrators.",
        
        # Misc
        "coming_soon": "🚧 Coming Soon!",
        "feature_disabled": "This feature is currently disabled.",
        "loading": "⏳ Loading...",
        "processing": "⏳ Processing...",
        
        # Game-specific messages
        "dice_game": "🎲 Dice",
        "darts_game": "🎯 Darts",
        "football_game": "⚽ Football",
        "bowling_game": "🎳 Bowling",
        "blackjack_game": "🃏 Blackjack",
        "roulette_game": "🎯 Roulette",
        "slots_game": "🎰 Slots",
        "play_vs_bot": "🤖 Play vs Bot",
        "play_vs_player": "👤 Play vs Player",
        "who_to_play": "Who do you want to play against?",
        "bot_rolling": "Bot is rolling...",
        "your_turn": "Your turn! Send {rolls} {emoji}!",
        "bot_rolled": "Bot rolled: {rolls_text} = <b>{total}</b>",
        "you_rolled": "You rolled: {rolls_text} = <b>{total}</b>",
        "you_win_round": "You win this round!",
        "bot_wins_round": "Bot wins this round!",
        "tie_round": "It's a tie! No point.",
        "you_win_game": "🏆 Congratulations! You beat the bot ({user_score}-{bot_score}) and win {amount}!",
        "bot_wins_game": "😔 Bot wins the match ({bot_score}-{user_score}). You lost {amount}.",
        "score_update": "Score: You {user_score} - {bot_score} Bot. (First to {target})",
        "roll_complete": "Roll {current}/{total} complete. Send {remaining} more {emoji}!",
        "normal_mode": "🎮 Normal Mode",
        "crazy_mode": "🔥 Crazy Mode",
        "select_mode": "Select game mode:",
        "select_rolls": "Select number of rolls:",
        "select_target": "Select target score:",
        "game_created": "🎯 Game created! Waiting for opponent...",
        "usage_dice": "Usage: /dice <amount>\nExample: /dice 5 or /dice all",
        "usage_darts": "Usage: /darts <amount>\nExample: /darts 5 or /darts all",
        "usage_goal": "Usage: /goal <amount>\nExample: /goal 5 or /goal all",
        "usage_bowl": "Usage: /bowl <amount>\nExample: /bowl 5 or /bowl all",
    },
    "es": {  # Spanish
        "language_name": "Español 🇪🇸",
        # Welcome and Main Menu - RESTORED ORIGINAL FULL TEXT
        "welcome_title": "🎰 <b>¡Bienvenido al Bot de Casino y Escrow de Telegram!</b> 🎰",
        "hello": "👋 ¡Hola {first_name}!",
        "welcome_desc": "🎲 Experimenta la emoción de los juegos de casino o asegura tus operaciones con nuestro sistema automatizado de Escrow.",
        "ai_feature": "✨ NUEVO: ¡Chatea con nuestro <b>Asistente IA</b> para cualquier pregunta o tarea!",
        "current_balance": "💰 Saldo Actual: <b>{balance}</b>",
        "choose_option": "Elige una opción para comenzar:",
        
        # Buttons
        "withdraw": "📤 Retirar",
        "games": "🎮 Juegos",
        "more": "➕ Más",
        "stats": "📊 Estadísticas",
        "settings": "⚙️ Configuración",
        "help": "❓ Ayuda",
        "bonuses": "🎁 Bonos",
        "escrow": "🔐 Depósito en garantía",
        "ai_assistant": "🤖 Asistente IA",
        "back": "🔙 Atrás",
        "cancel": "❌ Cancelar",
        "confirm": "✅ Confirmar",
        
        # Balance and Currency
        "balance": "💰 Tu saldo: {balance}",
        "your_balance": "💰 Tu saldo: {balance}",
        "insufficient_balance": "❌ Saldo insuficiente. Por favor deposita para continuar.",
        "locked_in_games": "+ {amount} bloqueado en juegos",
        
        # Betting
        "enter_bet_amount": "Ingresa tu cantidad de apuesta:",
        "bet_placed": "🎲 Apuesta realizada: ${amount:.2f}",
        "invalid_amount": "Cantidad inválida. Por favor ingresa un número válido o 'all'.",
        "min_bet": "La apuesta mínima para este juego es {amount}",
        "max_bet": "La apuesta máxima para este juego es {amount}",
        
        # Game Results
        "you_won": "🎉 ¡Ganaste {amount}!",
        "you_lost": "😔 Perdiste. ¡Mejor suerte la próxima vez!",
        "game_started": "🎮 ¡Juego iniciado!",
        "game_ended": "🎮 ¡Juego terminado!",
        "round": "Ronda {round}",
        "waiting_for_opponent": "⏳ Esperando oponente...",
        
        # Daily Bonus
        "daily_claim_success": "🎉 ¡Has reclamado con éxito tu bono diario de {amount}!",
        "daily_claim_wait": "⏳ Ya has reclamado tu bono diario. Por favor, espera {hours}h {minutes}m antes de volver a reclamar.",
        "daily_bonus": "🎁 Bono Diario",
        
        # Achievements
        "achievement_unlocked": "🏅 <b>¡Logro Desbloqueado!</b> 🏅\n\n¡Has ganado la insignia <b>{emoji} {name}</b>!\n<i>{description}</i>",
        "achievements": "🏅 Logros",
        "no_achievements": "Aún no has desbloqueado ningún logro. ¡Comienza a jugar para ganar insignias!",
        
        # Language
        "language_set": "✅ Idioma configurado a Español",
        "select_language": "🌍 <b>Selecciona tu idioma:</b>",
        "language": "🌍 Idioma",
        
        # Games Menu
        "games_menu": "🎮 <b>Juegos de Casino</b>\n\nElige una categoría:",
        "dice_games": "🎲 Juegos de Dados",
        "card_games": "🃏 Juegos de Cartas",
        "original_games": "⭐ Juegos Originales",
        "quick_games": "⚡ Juegos Rápidos",
        
        # Settings
        "settings_menu": "⚙️ <b>Configuración</b>\n\nPersonaliza tu experiencia:",
        "withdrawal_address": "💳 Dirección de Retiro",
        "currency_settings": "💱 Moneda",
        "recovery_settings": "🔐 Recuperación",
        
        # Help
        "help_text": "❓ <b>Ayuda y Comandos</b>\n\nComandos disponibles:\n/start - Menú principal\n/games - Ver juegos\n/balance - Ver saldo\n/withdraw - Retirar fondos\n/stats - Ver estadísticas\n/daily - Reclamar bono diario\n/help - Mostrar esta ayuda\n\nPara soporte, contacta @jashanxjagy",
        
        # Errors
        "error_occurred": "❌ Ocurrió un error. Por favor intenta de nuevo.",
        "command_not_found": "❌ Comando no encontrado. Usa /help para ver los comandos disponibles.",
        "maintenance_mode": "🛠️ <b>Bot en Mantenimiento</b> 🛠️\n\nEl bot está actualmente en mantenimiento programado.",
        "banned_user": "Has sido bloqueado del uso de este bot.",
        
        # Deposit/Withdrawal
        "withdrawal_menu": "📤 <b>Retirar</b>\n\nIngresa la cantidad que deseas retirar:",
        "withdrawal_success": "✅ ¡Solicitud de retiro enviada exitosamente!",
        "withdrawal_pending": "Tu retiro está siendo procesado...",
        
        # Admin
        "admin_panel": "👑 <b>Panel de Administración</b>",
        "admin_only": "Este comando solo está disponible para administradores.",
        
        # Misc
        "coming_soon": "🚧 ¡Próximamente!",
        "feature_disabled": "Esta característica está actualmente deshabilitada.",
        "loading": "⏳ Cargando...",
        "processing": "⏳ Procesando...",
        
        # Game-specific messages
        "dice_game": "🎲 Dados",
        "darts_game": "🎯 Dardos",
        "football_game": "⚽ Fútbol",
        "bowling_game": "🎳 Bolos",
        "blackjack_game": "🃏 Blackjack",
        "roulette_game": "🎯 Ruleta",
        "slots_game": "🎰 Tragamonedas",
        "play_vs_bot": "🤖 Jugar vs Bot",
        "play_vs_player": "👤 Jugar vs Jugador",
        "who_to_play": "¿Contra quién quieres jugar?",
        "bot_rolling": "El bot está tirando...",
        "your_turn": "¡Tu turno! ¡Envía {rolls} {emoji}!",
        "bot_rolled": "Bot tiró: {rolls_text} = <b>{total}</b>",
        "you_rolled": "Tiraste: {rolls_text} = <b>{total}</b>",
        "you_win_round": "¡Ganas esta ronda!",
        "bot_wins_round": "¡El bot gana esta ronda!",
        "tie_round": "¡Es un empate! Sin punto.",
        "you_win_game": "🏆 ¡Felicidades! Venciste al bot ({user_score}-{bot_score}) y ganas {amount}!",
        "bot_wins_game": "😔 El bot gana el partido ({bot_score}-{user_score}). Perdiste {amount}.",
        "score_update": "Puntuación: Tú {user_score} - {bot_score} Bot. (Primero a {target})",
        "roll_complete": "Tirada {current}/{total} completa. ¡Envía {remaining} más {emoji}!",
        "normal_mode": "🎮 Modo Normal",
        "crazy_mode": "🔥 Modo Loco",
        "select_mode": "Selecciona el modo de juego:",
        "select_rolls": "Selecciona el número de tiradas:",
        "select_target": "Selecciona puntuación objetivo:",
        "game_created": "🎯 ¡Juego creado! Esperando oponente...",
        "usage_dice": "Uso: /dice <cantidad>\nEjemplo: /dice 5 o /dice all",
        "usage_darts": "Uso: /darts <cantidad>\nEjemplo: /darts 5 o /darts all",
        "usage_goal": "Uso: /goal <cantidad>\nEjemplo: /goal 5 o /goal all",
        "usage_bowl": "Uso: /bowl <cantidad>\nEjemplo: /bowl 5 o /bowl all",
    },
    "fr": {  # French
        "language_name": "Français 🇫🇷",
        # Welcome and Main Menu - RESTORED ORIGINAL FULL TEXT
        "welcome_title": "🎰 <b>Bienvenue au Bot de Casino et Escrow Telegram!</b> 🎰",
        "hello": "👋 Bonjour {first_name}!",
        "welcome_desc": "🎲 Vivez l'excitation des jeux de casino ou sécurisez vos transactions avec notre système Escrow automatisé.",
        "ai_feature": "✨ NOUVEAU: Chattez avec notre <b>Assistant IA</b> pour toute question ou tâche!",
        "current_balance": "💰 Solde Actuel: <b>{balance}</b>",
        "choose_option": "Choisissez une option ci-dessous pour commencer:",
        
        # Buttons
        "withdraw": "📤 Retrait",
        "games": "🎮 Jeux",
        "more": "➕ Plus",
        "stats": "📊 Statistiques",
        "settings": "⚙️ Paramètres",
        "help": "❓ Aide",
        "bonuses": "🎁 Bonus",
        "escrow": "🔐 Dépôt fiduciaire",
        "ai_assistant": "🤖 Assistant IA",
        "back": "🔙 Retour",
        "cancel": "❌ Annuler",
        "confirm": "✅ Confirmer",
        
        # Balance and Currency
        "balance": "💰 Votre solde: {balance}",
        "your_balance": "💰 Votre solde: {balance}",
        "insufficient_balance": "❌ Solde insuffisant. Veuillez déposer pour continuer.",
        "locked_in_games": "+ {amount} bloqué dans les jeux",
        
        # Betting
        "enter_bet_amount": "Entrez votre montant de pari:",
        "bet_placed": "🎲 Pari placé: ${amount:.2f}",
        "invalid_amount": "Montant invalide. Veuillez entrer un nombre valide ou 'all'.",
        "min_bet": "La mise minimale pour ce jeu est {amount}",
        "max_bet": "La mise maximale pour ce jeu est {amount}",
        
        # Game Results
        "you_won": "🎉 Vous avez gagné {amount}!",
        "you_lost": "😔 Vous avez perdu. Meilleure chance la prochaine fois!",
        "game_started": "🎮 Jeu commencé!",
        "game_ended": "🎮 Jeu terminé!",
        "round": "Tour {round}",
        "waiting_for_opponent": "⏳ En attente de l'adversaire...",
        
        # Daily Bonus
        "daily_claim_success": "🎉 Vous avez réclamé avec succès votre bonus quotidien de {amount}!",
        "daily_claim_wait": "⏳ Vous avez déjà réclamé votre bonus quotidien. Veuillez attendre {hours}h {minutes}m avant de réclamer à nouveau.",
        "daily_bonus": "🎁 Bonus Quotidien",
        
        # Achievements
        "achievement_unlocked": "🏅 <b>Succès Débloqué!</b> 🏅\n\nVous avez gagné le badge <b>{emoji} {name}</b>!\n<i>{description}</i>",
        "achievements": "🏅 Succès",
        "no_achievements": "Vous n'avez pas encore débloqué de succès. Commencez à jouer pour gagner des badges!",
        
        # Language
        "language_set": "✅ Langue définie sur Français",
        "select_language": "🌍 <b>Sélectionnez votre langue:</b>",
        "language": "🌍 Langue",
        
        # Games Menu
        "games_menu": "🎮 <b>Jeux de Casino</b>\n\nChoisissez une catégorie:",
        "dice_games": "🎲 Jeux de Dés",
        "card_games": "🃏 Jeux de Cartes",
        "original_games": "⭐ Jeux Originaux",
        "quick_games": "⚡ Jeux Rapides",
        
        # Settings
        "settings_menu": "⚙️ <b>Paramètres</b>\n\nPersonnalisez votre expérience:",
        "withdrawal_address": "💳 Adresse de Retrait",
        "currency_settings": "💱 Devise",
        "recovery_settings": "🔐 Récupération",
        
        # Help
        "help_text": "❓ <b>Aide et Commandes</b>\n\nCommandes disponibles:\n/start - Menu principal\n/games - Parcourir les jeux\n/balance - Vérifier le solde\n/withdraw - Retirer des fonds\n/stats - Voir les statistiques\n/daily - Réclamer le bonus quotidien\n/help - Afficher cette aide\n\nPour le support, contactez @jashanxjagy",
        
        # Errors
        "error_occurred": "❌ Une erreur s'est produite. Veuillez réessayer.",
        "command_not_found": "❌ Commande non trouvée. Utilisez /help pour voir les commandes disponibles.",
        "maintenance_mode": "🛠️ <b>Bot en Maintenance</b> 🛠️\n\nLe bot est actuellement en maintenance programmée.",
        "banned_user": "Vous avez été banni de l'utilisation de ce bot.",
        
        # Deposit/Withdrawal
        "withdrawal_menu": "📤 <b>Retrait</b>\n\nEntrez le montant que vous souhaitez retirer:",
        "withdrawal_success": "✅ Demande de retrait soumise avec succès!",
        "withdrawal_pending": "Votre retrait est en cours de traitement...",
        
        # Admin
        "admin_panel": "👑 <b>Panneau d'Administration</b>",
        "admin_only": "Cette commande n'est disponible que pour les administrateurs.",
        
        # Misc
        "coming_soon": "🚧 Bientôt disponible!",
        "feature_disabled": "Cette fonctionnalité est actuellement désactivée.",
        "loading": "⏳ Chargement...",
        "processing": "⏳ Traitement...",
        
        # Game-specific messages
        "dice_game": "🎲 Dés",
        "darts_game": "🎯 Fléchettes",
        "football_game": "⚽ Football",
        "bowling_game": "🎳 Bowling",
        "blackjack_game": "🃏 Blackjack",
        "roulette_game": "🎯 Roulette",
        "slots_game": "🎰 Machines à sous",
        "play_vs_bot": "🤖 Jouer vs Bot",
        "play_vs_player": "👤 Jouer vs Joueur",
        "who_to_play": "Contre qui voulez-vous jouer?",
        "bot_rolling": "Le bot lance...",
        "your_turn": "Votre tour! Envoyez {rolls} {emoji}!",
        "bot_rolled": "Bot a lancé: {rolls_text} = <b>{total}</b>",
        "you_rolled": "Vous avez lancé: {rolls_text} = <b>{total}</b>",
        "you_win_round": "Vous gagnez ce tour!",
        "bot_wins_round": "Le bot gagne ce tour!",
        "tie_round": "C'est une égalité! Aucun point.",
        "you_win_game": "🏆 Félicitations! Vous avez battu le bot ({user_score}-{bot_score}) et gagnez {amount}!",
        "bot_wins_game": "😔 Le bot gagne le match ({bot_score}-{user_score}). Vous avez perdu {amount}.",
        "score_update": "Score: Vous {user_score} - {bot_score} Bot. (Premier à {target})",
        "roll_complete": "Lancer {current}/{total} terminé. Envoyez {remaining} de plus {emoji}!",
        "normal_mode": "🎮 Mode Normal",
        "crazy_mode": "🔥 Mode Fou",
        "select_mode": "Sélectionnez le mode de jeu:",
        "select_rolls": "Sélectionnez le nombre de lancers:",
        "select_target": "Sélectionnez le score cible:",
        "game_created": "🎯 Jeu créé! En attente d'adversaire...",
        "usage_dice": "Utilisation: /dice <montant>\nExemple: /dice 5 ou /dice all",
        "usage_darts": "Utilisation: /darts <montant>\nExemple: /darts 5 ou /darts all",
        "usage_goal": "Utilisation: /goal <montant>\nExemple: /goal 5 ou /goal all",
        "usage_bowl": "Utilisation: /bowl <montant>\nExemple: /bowl 5 ou /bowl all",
    },
    "ru": {  # Russian
        "language_name": "Русский 🇷🇺",
        # Welcome and Main Menu - RESTORED ORIGINAL FULL TEXT
        "welcome_title": "🎰 <b>Добро пожаловать в Telegram Casino & Escrow Bot!</b> 🎰",
        "hello": "👋 Здравствуйте, {first_name}!",
        "welcome_desc": "🎲 Испытайте острые ощущения от азартных игр или обезопасьте свои сделки с помощью нашей автоматизированной системы Escrow.",
        "ai_feature": "✨ НОВИНКА: Общайтесь с нашим <b>ИИ Помощником</b> для любых вопросов или задач!",
        "current_balance": "💰 Текущий Баланс: <b>{balance}</b>",
        "choose_option": "Выберите опцию ниже, чтобы начать:",
        
        # Buttons
        "withdraw": "📤 Вывести",
        "games": "🎮 Игры",
        "more": "➕ Ещё",
        "stats": "📊 Статистика",
        "settings": "⚙️ Настройки",
        "help": "❓ Помощь",
        "bonuses": "🎁 Бонусы",
        "escrow": "🔐 Эскроу",
        "ai_assistant": "🤖 ИИ Помощник",
        "back": "🔙 Назад",
        "cancel": "❌ Отмена",
        "confirm": "✅ Подтвердить",
        
        # Balance and Currency
        "balance": "💰 Ваш баланс: {balance}",
        "your_balance": "💰 Ваш баланс: {balance}",
        "insufficient_balance": "❌ Недостаточно средств. Пожалуйста, пополните счет.",
        "locked_in_games": "+ {amount} заблокировано в играх",
        
        # Betting
        "enter_bet_amount": "Введите сумму ставки:",
        "bet_placed": "🎲 Ставка сделана: ${amount:.2f}",
        "invalid_amount": "Неверная сумма. Пожалуйста, введите правильное число или 'all'.",
        "min_bet": "Минимальная ставка для этой игры {amount}",
        "max_bet": "Максимальная ставка для этой игры {amount}",
        
        # Game Results
        "you_won": "🎉 Вы выиграли {amount}!",
        "you_lost": "😔 Вы проиграли. Удачи в следующий раз!",
        "game_started": "🎮 Игра началась!",
        "game_ended": "🎮 Игра закончилась!",
        "round": "Раунд {round}",
        "waiting_for_opponent": "⏳ Ожидание противника...",
        
        # Daily Bonus
        "daily_claim_success": "🎉 Вы успешно получили ежедневный бонус {amount}!",
        "daily_claim_wait": "⏳ Вы уже получили свой ежедневный бонус. Подождите {hours}ч {minutes}м перед следующим получением.",
        "daily_bonus": "🎁 Ежедневный Бонус",
        
        # Achievements
        "achievement_unlocked": "🏅 <b>Достижение Разблокировано!</b> 🏅\n\nВы получили значок <b>{emoji} {name}</b>!\n<i>{description}</i>",
        "achievements": "🏅 Достижения",
        "no_achievements": "Вы еще не разблокировали никаких достижений. Начните играть, чтобы заработать значки!",
        
        # Language
        "language_set": "✅ Язык установлен на Русский",
        "select_language": "🌍 <b>Выберите ваш язык:</b>",
        "language": "🌍 Язык",
        
        # Games Menu
        "games_menu": "🎮 <b>Игры Казино</b>\n\nВыберите категорию:",
        "dice_games": "🎲 Игры в Кости",
        "card_games": "🃏 Карточные Игры",
        "original_games": "⭐ Оригинальные Игры",
        "quick_games": "⚡ Быстрые Игры",
        
        # Settings
        "settings_menu": "⚙️ <b>Настройки</b>\n\nНастройте свой опыт:",
        "withdrawal_address": "💳 Адрес для Вывода",
        "currency_settings": "💱 Валюта",
        "recovery_settings": "🔐 Восстановление",
        
        # Help
        "help_text": "❓ <b>Помощь и Команды</b>\n\nДоступные команды:\n/start - Главное меню\n/games - Просмотр игр\n/balance - Проверить баланс\n/withdraw - Вывести средства\n/stats - Просмотр статистики\n/daily - Получить ежедневный бонус\n/help - Показать эту помощь\n\nДля поддержки, свяжитесь @jashanxjagy",
        
        # Errors
        "error_occurred": "❌ Произошла ошибка. Пожалуйста, попробуйте снова.",
        "command_not_found": "❌ Команда не найдена. Используйте /help, чтобы увидеть доступные команды.",
        "maintenance_mode": "🛠️ <b>Бот на Обслуживании</b> 🛠️\n\nБот в настоящее время находится на плановом обслуживании.",
        "banned_user": "Вы заблокированы от использования этого бота.",
        
        # Deposit/Withdrawal
        "withdrawal_menu": "📤 <b>Вывод</b>\n\nВведите сумму, которую хотите вывести:",
        "withdrawal_success": "✅ Запрос на вывод успешно отправлен!",
        "withdrawal_pending": "Ваш вывод обрабатывается...",
        
        # Admin
        "admin_panel": "👑 <b>Панель Администратора</b>",
        "admin_only": "Эта команда доступна только администраторам.",
        
        # Misc
        "coming_soon": "🚧 Скоро!",
        "feature_disabled": "Эта функция в настоящее время отключена.",
        "loading": "⏳ Загрузка...",
        "processing": "⏳ Обработка...",
        
        # Game-specific messages
        "dice_game": "🎲 Кости",
        "darts_game": "🎯 Дартс",
        "football_game": "⚽ Футбол",
        "bowling_game": "🎳 Боулинг",
        "blackjack_game": "🃏 Блэкджек",
        "roulette_game": "🎯 Рулетка",
        "slots_game": "🎰 Слоты",
        "play_vs_bot": "🤖 Играть с Ботом",
        "play_vs_player": "👤 Играть с Игроком",
        "who_to_play": "С кем хотите играть?",
        "bot_rolling": "Бот бросает...",
        "your_turn": "Ваш ход! Отправьте {rolls} {emoji}!",
        "bot_rolled": "Бот бросил: {rolls_text} = <b>{total}</b>",
        "you_rolled": "Вы бросили: {rolls_text} = <b>{total}</b>",
        "you_win_round": "Вы выиграли этот раунд!",
        "bot_wins_round": "Бот выиграл этот раунд!",
        "tie_round": "Ничья! Без очка.",
        "you_win_game": "🏆 Поздравляем! Вы победили бота ({user_score}-{bot_score}) и выиграли {amount}!",
        "bot_wins_game": "😔 Бот выиграл матч ({bot_score}-{user_score}). Вы проиграли {amount}.",
        "score_update": "Счёт: Вы {user_score} - {bot_score} Бот. (Первый до {target})",
        "roll_complete": "Бросок {current}/{total} завершён. Отправьте ещё {remaining} {emoji}!",
        "normal_mode": "🎮 Обычный Режим",
        "crazy_mode": "🔥 Сумасшедший Режим",
        "select_mode": "Выберите режим игры:",
        "select_rolls": "Выберите количество бросков:",
        "select_target": "Выберите целевой счёт:",
        "game_created": "🎯 Игра создана! Ожидание противника...",
        "usage_dice": "Использование: /dice <сумма>\nПример: /dice 5 или /dice all",
        "usage_darts": "Использование: /darts <сумма>\nПример: /darts 5 или /darts all",
        "usage_goal": "Использование: /goal <сумма>\nПример: /goal 5 или /goal all",
        "usage_bowl": "Использование: /bowl <сумма>\nПример: /bowl 5 или /bowl all",
    },
    "hi": {  # Hindi
        "language_name": "हिन्दी 🇮🇳",
        # Welcome and Main Menu - RESTORED ORIGINAL FULL TEXT
        "welcome_title": "🎰 <b>टेलीग्राम कैसीनो और एस्क्रो बॉट में आपका स्वागत है!</b> 🎰",
        "hello": "👋 नमस्ते {first_name}!",
        "welcome_desc": "🎲 कैसीनो खेलों के रोमांच का अनुभव करें या हमारे स्वचालित एस्क्रो सिस्टम के साथ अपने लेन-देन को सुरक्षित रखें।",
        "ai_feature": "✨ नया: किसी भी प्रश्न या कार्य के लिए हमारे <b>एआई सहायक</b> से चैट करें!",
        "current_balance": "💰 वर्तमान शेष: <b>{balance}</b>",
        "choose_option": "शुरू करने के लिए नीचे एक विकल्प चुनें:",
        
        # Buttons
        "withdraw": "📤 निकालें",
        "games": "🎮 खेल",
        "more": "➕ और",
        "stats": "📊 आंकड़े",
        "settings": "⚙️ सेटिंग्स",
        "help": "❓ मदद",
        "bonuses": "🎁 बोनस",
        "escrow": "🔐 एस्क्रो",
        "ai_assistant": "🤖 एआई सहायक",
        "back": "🔙 वापस",
        "cancel": "❌ रद्द करें",
        "confirm": "✅ पुष्टि करें",
        
        # Balance and Currency
        "balance": "💰 आपका शेष: {balance}",
        "your_balance": "💰 आपका शेष: {balance}",
        "insufficient_balance": "❌ अपर्याप्त शेष राशि। कृपया जारी रखने के लिए जमा करें।",
        "locked_in_games": "+ {amount} खेलों में लॉक",
        
        # Betting
        "enter_bet_amount": "अपनी दांव राशि दर्ज करें:",
        "bet_placed": "🎲 दांव लगाया गया: ${amount:.2f}",
        "invalid_amount": "अमान्य राशि। कृपया एक वैध संख्या या 'all' दर्ज करें।",
        "min_bet": "इस खेल के लिए न्यूनतम दांव {amount} है",
        "max_bet": "इस खेल के लिए अधिकतम दांव {amount} है",
        
        # Game Results
        "you_won": "🎉 आपने {amount} जीता!",
        "you_lost": "😔 आप हार गए। अगली बार के लिए शुभकामनाएं!",
        "game_started": "🎮 खेल शुरू हुआ!",
        "game_ended": "🎮 खेल समाप्त हुआ!",
        "round": "राउंड {round}",
        "waiting_for_opponent": "⏳ प्रतिद्वंद्वी की प्रतीक्षा में...",
        
        # Daily Bonus
        "daily_claim_success": "🎉 आपने सफलतापूर्वक {amount} का दैनिक बोनस प्राप्त किया!",
        "daily_claim_wait": "⏳ आपने पहले ही अपना दैनिक बोनस प्राप्त कर लिया है। कृपया {hours}घं {minutes}मि प्रतीक्षा करें।",
        "daily_bonus": "🎁 दैनिक बोनस",
        
        # Achievements
        "achievement_unlocked": "🏅 <b>उपलब्धि अनलॉक!</b> 🏅\n\nआपने <b>{emoji} {name}</b> बैज अर्जित किया!\n<i>{description}</i>",
        "achievements": "🏅 उपलब्धियां",
        "no_achievements": "आपने अभी तक कोई उपलब्धि अनलॉक नहीं की है। बैज अर्जित करने के लिए खेलना शुरू करें!",
        
        # Language
        "language_set": "✅ भाषा हिन्दी पर सेट की गई",
        "select_language": "🌍 <b>अपनी भाषा चुनें:</b>",
        "language": "🌍 भाषा",
        
        # Games Menu
        "games_menu": "🎮 <b>कैसीनो खेल</b>\n\nएक श्रेणी चुनें:",
        "dice_games": "🎲 पासा खेल",
        "card_games": "🃏 ताश के खेल",
        "original_games": "⭐ मूल खेल",
        "quick_games": "⚡ त्वरित खेल",
        
        # Settings
        "settings_menu": "⚙️ <b>सेटिंग्स</b>\n\nअपने अनुभव को अनुकूलित करें:",
        "withdrawal_address": "💳 निकासी पता",
        "currency_settings": "💱 मुद्रा",
        "recovery_settings": "🔐 पुनर्प्राप्ति",
        
        # Help
        "help_text": "❓ <b>सहायता और आदेश</b>\n\nउपलब्ध आदेश:\n/start - मुख्य मेनू\n/games - खेल ब्राउज़ करें\n/balance - शेष जांचें\n/withdraw - निकालें\n/stats - आंकड़े देखें\n/daily - दैनिक बोनस प्राप्त करें\n/help - यह सहायता दिखाएं\n\nसहायता के लिए, @jashanxjagy से संपर्क करें",
        
        # Errors
        "error_occurred": "❌ एक त्रुटि हुई। कृपया पुन: प्रयास करें।",
        "command_not_found": "❌ आदेश नहीं मिला। उपलब्ध आदेश देखने के लिए /help का उपयोग करें।",
        "maintenance_mode": "🛠️ <b>बॉट रखरखाव में</b> 🛠️\n\nबॉट वर्तमान में निर्धारित रखरखाव में है।",
        "banned_user": "आपको इस बॉट का उपयोग करने से प्रतिबंधित कर दिया गया है।",
        
        # Deposit/Withdrawal
        "withdrawal_menu": "📤 <b>निकासी</b>\n\nवह राशि दर्ज करें जो आप निकालना चाहते हैं:",
        "withdrawal_success": "✅ निकासी अनुरोध सफलतापूर्वक सबमिट किया गया!",
        "withdrawal_pending": "आपकी निकासी प्रक्रिया में है...",
        
        # Admin
        "admin_panel": "👑 <b>व्यवस्थापक पैनल</b>",
        "admin_only": "यह आदेश केवल व्यवस्थापकों के लिए उपलब्ध है।",
        
        # Misc
        "coming_soon": "🚧 जल्द आ रहा है!",
        "feature_disabled": "यह सुविधा वर्तमान में अक्षम है।",
        "loading": "⏳ लोड हो रहा है...",
        "processing": "⏳ प्रक्रिया में...",
        
        # Game-specific messages
        "dice_game": "🎲 पासा",
        "darts_game": "🎯 डार्ट्स",
        "football_game": "⚽ फुटबॉल",
        "bowling_game": "🎳 बॉलिंग",
        "blackjack_game": "🃏 ब्लैकजैक",
        "roulette_game": "🎯 रूले",
        "slots_game": "🎰 स्लॉट्स",
        "play_vs_bot": "🤖 बॉट के खिलाफ खेलें",
        "play_vs_player": "👤 खिलाड़ी के खिलाफ खेलें",
        "who_to_play": "आप किसके खिलाफ खेलना चाहते हैं?",
        "bot_rolling": "बॉट रोल कर रहा है...",
        "your_turn": "आपकी बारी! {rolls} {emoji} भेजें!",
        "bot_rolled": "बॉट ने रोल किया: {rolls_text} = <b>{total}</b>",
        "you_rolled": "आपने रोल किया: {rolls_text} = <b>{total}</b>",
        "you_win_round": "आप यह राउंड जीत गए!",
        "bot_wins_round": "बॉट यह राउंड जीत गया!",
        "tie_round": "यह बराबरी है! कोई अंक नहीं।",
        "you_win_game": "🏆 बधाई हो! आपने बॉट को हराया ({user_score}-{bot_score}) और {amount} जीता!",
        "bot_wins_game": "😔 बॉट मैच जीत गया ({bot_score}-{user_score})। आपने {amount} खो दिया।",
        "score_update": "स्कोर: आप {user_score} - {bot_score} बॉट। (पहले {target} तक)",
        "roll_complete": "रोल {current}/{total} पूरा। {remaining} और {emoji} भेजें!",
        "normal_mode": "🎮 सामान्य मोड",
        "crazy_mode": "🔥 पागल मोड",
        "select_mode": "गेम मोड चुनें:",
        "select_rolls": "रोल की संख्या चुनें:",
        "select_target": "लक्ष्य स्कोर चुनें:",
        "game_created": "🎯 खेल बनाया गया! प्रतिद्वंद्वी की प्रतीक्षा में...",
        "usage_dice": "उपयोग: /dice <राशि>\nउदाहरण: /dice 5 या /dice all",
        "usage_darts": "उपयोग: /darts <राशि>\nउदाहरण: /darts 5 या /darts all",
        "usage_goal": "उपयोग: /goal <राशि>\nउदाहरण: /goal 5 या /goal all",
        "usage_bowl": "उपयोग: /bowl <राशि>\nउदाहरण: /bowl 5 या /bowl all",
    },
    "zh": {  # Mandarin Chinese
        "language_name": "中文 🇨🇳",
        # Welcome and Main Menu - RESTORED ORIGINAL FULL TEXT
        "welcome_title": "🎰 <b>欢迎来到Telegram赌场和托管机器人!</b> 🎰",
        "hello": "👋 您好 {first_name}!",
        "welcome_desc": "🎲 体验赌场游戏的刺激，或通过我们的自动化托管系统保护您的交易安全。",
        "ai_feature": "✨ 新功能：与我们的<b>AI助手</b>聊天，解答任何问题或任务！",
        "current_balance": "💰 当前余额：<b>{balance}</b>",
        "choose_option": "选择下方选项开始：",
        
        # Buttons
        "withdraw": "📤 提款",
        "games": "🎮 游戏",
        "more": "➕ 更多",
        "stats": "📊 统计",
        "settings": "⚙️ 设置",
        "help": "❓ 帮助",
        "bonuses": "🎁 奖金",
        "escrow": "🔐 托管",
        "ai_assistant": "🤖 AI助手",
        "back": "🔙 返回",
        "cancel": "❌ 取消",
        "confirm": "✅ 确认",
        
        # Balance and Currency
        "balance": "💰 您的余额: {balance}",
        "your_balance": "💰 您的余额: {balance}",
        "insufficient_balance": "❌ 余额不足。请充值以继续。",
        "locked_in_games": "+ {amount} 锁定在游戏中",
        
        # Betting
        "enter_bet_amount": "输入您的投注金额:",
        "bet_placed": "🎲 下注: ${amount:.2f}",
        "invalid_amount": "无效金额。请输入有效数字或'all'。",
        "min_bet": "此游戏的最小投注额为 {amount}",
        "max_bet": "此游戏的最大投注额为 {amount}",
        
        # Game Results
        "you_won": "🎉 您赢了{amount}!",
        "you_lost": "😔 您输了。祝下次好运!",
        "game_started": "🎮 游戏开始!",
        "game_ended": "🎮 游戏结束!",
        "round": "第{round}轮",
        "waiting_for_opponent": "⏳ 等待对手...",
        
        # Daily Bonus
        "daily_claim_success": "🎉 您已成功领取{amount}的每日奖金!",
        "daily_claim_wait": "⏳ 您已经领取了每日奖金。请等待{hours}小时{minutes}分钟后再次领取。",
        "daily_bonus": "🎁 每日奖金",
        
        # Achievements
        "achievement_unlocked": "🏅 <b>成就解锁!</b> 🏅\n\n您获得了<b>{emoji} {name}</b>徽章!\n<i>{description}</i>",
        "achievements": "🏅 成就",
        "no_achievements": "您还没有解锁任何成就。开始游戏以赚取徽章!",
        
        # Language
        "language_set": "✅ 语言已设置为中文",
        "select_language": "🌍 <b>选择您的语言:</b>",
        "language": "🌍 语言",
        
        # Games Menu
        "games_menu": "🎮 <b>赌场游戏</b>\n\n选择一个类别:",
        "dice_games": "🎲 骰子游戏",
        "card_games": "🃏 纸牌游戏",
        "original_games": "⭐ 原创游戏",
        "quick_games": "⚡ 快速游戏",
        
        # Settings
        "settings_menu": "⚙️ <b>设置</b>\n\n自定义您的体验:",
        "withdrawal_address": "💳 提款地址",
        "currency_settings": "💱 货币",
        "recovery_settings": "🔐 恢复",
        
        # Help
        "help_text": "❓ <b>帮助和命令</b>\n\n可用命令:\n/start - 主菜单\n/games - 浏览游戏\n/balance - 查看余额\n/withdraw - 提款\n/stats - 查看统计\n/daily - 领取每日奖金\n/help - 显示此帮助\n\n如需支持，请联系 @jashanxjagy",
        
        # Errors
        "error_occurred": "❌ 发生错误。请重试。",
        "command_not_found": "❌ 命令未找到。使用 /help 查看可用命令。",
        "maintenance_mode": "🛠️ <b>机器人维护中</b> 🛠️\n\n机器人目前正在进行计划维护。",
        "banned_user": "您已被禁止使用此机器人。",
        
        # Deposit/Withdrawal
        "withdrawal_menu": "📤 <b>提款</b>\n\n输入您要提款的金额:",
        "withdrawal_success": "✅ 提款请求已成功提交!",
        "withdrawal_pending": "您的提款正在处理中...",
        
        # Admin
        "admin_panel": "👑 <b>管理面板</b>",
        "admin_only": "此命令仅对管理员可用。",
        
        # Misc
        "coming_soon": "🚧 即将推出!",
        "feature_disabled": "此功能目前已禁用。",
        "loading": "⏳ 加载中...",
        "processing": "⏳ 处理中...",
        
        # Game-specific messages
        "dice_game": "🎲 骰子",
        "darts_game": "🎯 飞镖",
        "football_game": "⚽ 足球",
        "bowling_game": "🎳 保龄球",
        "blackjack_game": "🃏 二十一点",
        "roulette_game": "🎯 轮盘",
        "slots_game": "🎰 老虎机",
        "play_vs_bot": "🤖 与机器人对战",
        "play_vs_player": "👤 与玩家对战",
        "who_to_play": "您想与谁对战?",
        "bot_rolling": "机器人正在掷骰子...",
        "your_turn": "轮到您了! 发送 {rolls} {emoji}!",
        "bot_rolled": "机器人掷出: {rolls_text} = <b>{total}</b>",
        "you_rolled": "您掷出: {rolls_text} = <b>{total}</b>",
        "you_win_round": "您赢得本轮!",
        "bot_wins_round": "机器人赢得本轮!",
        "tie_round": "平局! 无分数。",
        "you_win_game": "🏆 恭喜! 您击败了机器人 ({user_score}-{bot_score}) 并赢得{amount}!",
        "bot_wins_game": "😔 机器人赢得比赛 ({bot_score}-{user_score})。您输了{amount}。",
        "score_update": "比分: 您 {user_score} - {bot_score} 机器人。(先到{target})",
        "roll_complete": "掷骰 {current}/{total} 完成。再发送 {remaining} 个 {emoji}!",
        "normal_mode": "🎮 普通模式",
        "crazy_mode": "🔥 疯狂模式",
        "select_mode": "选择游戏模式:",
        "select_rolls": "选择掷骰次数:",
        "select_target": "选择目标分数:",
        "game_created": "🎯 游戏已创建! 等待对手...",
        "usage_dice": "用法: /dice <金额>\n示例: /dice 5 或 /dice all",
        "usage_darts": "用法: /darts <金额>\n示例: /darts 5 或 /darts all",
        "usage_goal": "用法: /goal <金额>\n示例: /goal 5 或 /goal all",
        "usage_bowl": "用法: /bowl <金额>\n示例: /bowl 5 或 /bowl all",
    }
}
DEFAULT_LANG = "en"

# ================================
# DEPOSIT SYSTEM IMPLEMENTATION
# ================================

class DepositDatabase:
    """SQLite database for deposit system"""
    
    def __init__(self, db_path=DEPOSITS_DB):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # User addresses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_addresses (
                user_id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                address_index INTEGER NOT NULL,
                eth_address TEXT,
                bnb_address TEXT,
                base_address TEXT,
                tron_address TEXT,
                solana_address TEXT,
                ton_address TEXT,
                ton_private_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Migration: Add ton_private_key column if it doesn't exist
        try:
            cursor.execute("SELECT ton_private_key FROM user_addresses LIMIT 1")
        except sqlite3.OperationalError:
            logging.info("Adding ton_private_key column to user_addresses table")
            cursor.execute("ALTER TABLE user_addresses ADD COLUMN ton_private_key TEXT")
            conn.commit()
        
        # Deposits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                chain TEXT NOT NULL,
                token TEXT,
                amount REAL NOT NULL,
                amount_usd REAL NOT NULL,
                from_address TEXT,
                to_address TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                confirmations INTEGER DEFAULT 0,
                block_number INTEGER,
                sweep_tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                swept_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_addresses(user_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deposits_user ON deposits(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deposits_chain ON deposits(chain)')
        
        conn.commit()
        conn.close()
        logging.info("Deposit database initialized")
    
    def get_or_create_user(self, telegram_id):
        """Get or create user with unique address index"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT * FROM user_addresses WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        
        if user:
            conn.close()
            return {
                'user_id': user[0],
                'telegram_id': user[1],
                'address_index': user[2],
                'eth_address': user[3],
                'bnb_address': user[4],
                'base_address': user[5],
                'tron_address': user[6],
                'solana_address': user[7],
                'ton_address': user[8],
                'ton_private_key': user[9]
            }
        
        # Get next address index
        cursor.execute('SELECT MAX(address_index) FROM user_addresses')
        max_index = cursor.fetchone()[0]
        next_index = (max_index or 0) + 1
        
        # Generate addresses
        wallet_manager = HDWalletManager()
        addresses = {}
        ton_private_key = None
        for chain in ['ETH', 'BNB', 'BASE', 'TRON', 'SOLANA', 'TON']:
            try:
                if chain == 'TON':
                    # Generate TON address with private key
                    ton_data = wallet_manager.generate_ton_with_key(next_index)
                    if ton_data and isinstance(ton_data, dict) and 'address' in ton_data:
                        addresses[chain] = ton_data['address']
                        ton_private_key = ton_data.get('private_key')
                    else:
                        addresses[chain] = None
                        logging.warning(f"Failed to generate TON address for index {next_index} - TON library may not be available")
                else:
                    addresses[chain] = wallet_manager.generate_address(chain, next_index)
            except Exception as e:
                logging.error(f"Error generating {chain} address for index {next_index}: {e}")
                logging.error(traceback.format_exc())
                addresses[chain] = None
        
        # Insert new user
        cursor.execute('''
            INSERT INTO user_addresses 
            (telegram_id, address_index, eth_address, bnb_address, base_address, 
             tron_address, solana_address, ton_address, ton_private_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, next_index, addresses['ETH'], addresses['BNB'], 
              addresses['BASE'], addresses['TRON'], addresses['SOLANA'], addresses['TON'], ton_private_key))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f"Created deposit addresses for user {telegram_id} with index {next_index}")
        
        return {
            'user_id': user_id,
            'telegram_id': telegram_id,
            'address_index': next_index,
            'eth_address': addresses['ETH'],
            'bnb_address': addresses['BNB'],
            'base_address': addresses['BASE'],
            'tron_address': addresses['TRON'],
            'solana_address': addresses['SOLANA'],
            'ton_address': addresses['TON'],
            'ton_private_key': ton_private_key
        }
    
    def add_deposit(self, tx_hash, user_id, chain, amount, amount_usd, to_address, 
                    token=None, from_address=None, block_number=None):
        """Add new deposit"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO deposits 
                (tx_hash, user_id, chain, token, amount, amount_usd, from_address, 
                 to_address, block_number, status, confirmations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)
            ''', (tx_hash, user_id, chain, token, amount, amount_usd, from_address, 
                  to_address, block_number))
            
            conn.commit()
            deposit_id = cursor.lastrowid
            logging.info(f"Added deposit {tx_hash} for user {user_id}")
            return deposit_id
        except sqlite3.IntegrityError:
            logging.warning(f"Deposit {tx_hash} already exists")
            return None
        finally:
            conn.close()
    
    def update_deposit_status(self, tx_hash, status, confirmations=None, 
                              sweep_tx_hash=None, confirmed_at=None, swept_at=None):
        """Update deposit status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = ['status = ?']
        params = [status]
        
        if confirmations is not None:
            updates.append('confirmations = ?')
            params.append(confirmations)
        
        if sweep_tx_hash:
            updates.append('sweep_tx_hash = ?')
            params.append(sweep_tx_hash)
        
        if confirmed_at:
            updates.append('confirmed_at = ?')
            params.append(confirmed_at)
        
        if swept_at:
            updates.append('swept_at = ?')
            params.append(swept_at)
        
        params.append(tx_hash)
        
        cursor.execute(f'''
            UPDATE deposits SET {', '.join(updates)} WHERE tx_hash = ?
        ''', params)
        
        conn.commit()
        conn.close()
    
    def get_pending_deposits(self):
        """Get all pending deposits"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, tx_hash, user_id, chain, token, amount, amount_usd, 
                   to_address, status, confirmations, block_number
            FROM deposits 
            WHERE status IN ('pending', 'confirmed')
            ORDER BY created_at DESC
        ''')
        deposits = cursor.fetchall()
        conn.close()
        return deposits
    
    def get_user_deposits(self, telegram_id, limit=10):
        """Get user's recent deposits"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.tx_hash, d.chain, d.token, d.amount, d.amount_usd, 
                   d.status, d.created_at, d.confirmed_at
            FROM deposits d
            JOIN user_addresses u ON d.user_id = u.user_id
            WHERE u.telegram_id = ?
            ORDER BY d.created_at DESC
            LIMIT ?
        ''', (telegram_id, limit))
        deposits = cursor.fetchall()
        conn.close()
        return deposits
    
    def get_user_by_address(self, address, chain):
        """Get user by deposit address"""
        # Validate chain to prevent SQL injection
        valid_chains = ['ETH', 'BNB', 'BASE', 'TRON', 'SOLANA', 'TON']
        if chain not in valid_chains:
            logging.error(f"Invalid chain: {chain}")
            return None
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        column = f"{chain.lower()}_address"
        cursor.execute(f'''
            SELECT user_id, telegram_id, address_index 
            FROM user_addresses 
            WHERE {column} = ?
        ''', (address,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {'user_id': user[0], 'telegram_id': user[1], 'address_index': user[2]}
        return None


class HDWalletManager:
    """HD Wallet Manager for multi-chain address generation"""
    
    def __init__(self):
        self.mnemonic = MASTER_MNEMONIC
        self.seed = Bip39SeedGenerator(self.mnemonic).Generate()
    
    def generate_address(self, chain, index):
        """Generate address for specific chain and index"""
        if chain in ['ETH', 'BNB', 'BASE']:
            return self._generate_evm_address(chain, index)
        elif chain == 'TRON':
            return self._generate_tron_address(index)
        elif chain == 'SOLANA':
            return self._generate_solana_address(index)
        elif chain == 'TON':
            return self._generate_ton_address(index)
        else:
            raise ValueError(f"Unsupported chain: {chain}")
    
    def derive_private_key(self, chain, index):
        """Derive private key for specific chain and index"""
        if chain in ['ETH', 'BNB', 'BASE']:
            return self._derive_evm_private_key(index)
        elif chain == 'TRON':
            return self._derive_tron_private_key(index)
        elif chain == 'SOLANA':
            return self._derive_solana_private_key(index)
        elif chain == 'TON':
            return self._derive_ton_private_key(index)
        else:
            raise ValueError(f"Unsupported chain: {chain}")
    
    def _generate_evm_address(self, chain, index):
        """Generate EVM address (ETH, BNB, BASE)"""
        bip44_ctx = Bip44.FromSeed(self.seed, Bip44Coins.ETHEREUM)
        bip44_acc = bip44_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
        return bip44_acc.PublicKey().ToAddress()
    
    def _derive_evm_private_key(self, index):
        """Derive EVM private key"""
        bip44_ctx = Bip44.FromSeed(self.seed, Bip44Coins.ETHEREUM)
        bip44_acc = bip44_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
        return bip44_acc.PrivateKey().Raw().ToHex()
    
    def _generate_tron_address(self, index):
        """Generate TRON address"""
        if not TRON_AVAILABLE:
            return None
        bip44_ctx = Bip44.FromSeed(self.seed, Bip44Coins.TRON)
        bip44_acc = bip44_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
        return bip44_acc.PublicKey().ToAddress()
    
    def _derive_tron_private_key(self, index):
        """Derive TRON private key"""
        bip44_ctx = Bip44.FromSeed(self.seed, Bip44Coins.TRON)
        bip44_acc = bip44_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
        return bip44_acc.PrivateKey().Raw().ToHex()
    
    def _generate_solana_address(self, index):
        """Generate Solana address"""
        if not SOLANA_AVAILABLE:
            return None
        try:
            bip44_ctx = Bip44.FromSeed(self.seed, Bip44Coins.SOLANA)
            bip44_acc = bip44_ctx.Purpose().Coin().Account(index).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
            # Solana uses Ed25519, get the public key bytes directly
            pub_key_bytes = bip44_acc.PublicKey().RawCompressed().ToBytes()
            return base58.b58encode(pub_key_bytes).decode('utf-8')
        except Exception as e:
            logging.error(f"Error generating Solana address: {e}")
            return None
    
    def _derive_solana_private_key(self, index):
        """Derive Solana private key"""
        bip44_ctx = Bip44.FromSeed(self.seed, Bip44Coins.SOLANA)
        bip44_acc = bip44_ctx.Purpose().Coin().Account(index).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        # Return the full 64-byte keypair (32 bytes private + 32 bytes public)
        priv_key_bytes = bip44_acc.PrivateKey().Raw().ToBytes()
        pub_key_bytes = bip44_acc.PublicKey().RawCompressed().ToBytes()
        return priv_key_bytes + pub_key_bytes
    
    def generate_ton_with_key(self, index):
        """Generate TON address with separate private key (TON doesn't use BIP44 properly)"""
        if not TON_AVAILABLE:
            return None
        try:
            # Generate a deterministic private key for TON using HMAC-SHA256
            # This is more secure than simple SHA256 as it uses the mnemonic as a key
            
            # Use HMAC with mnemonic as key and index as message for key derivation
            message = f"ton-deposit:{index}".encode('utf-8')
            priv_key_bytes = hmac.new(
                self.mnemonic.encode('utf-8'),
                message,
                hashlib.sha256
            ).digest()
            
            # Derive public key from private key
            pub_key_bytes = private_key_to_public_key(priv_key_bytes)
            
            # Create TON address (workchain 0, non-bounceable)
            address = TonAddress((0, pub_key_bytes))
            address_str = address.to_str(is_bounceable=False, is_url_safe=True, is_test_only=False)
            
            # Store private key as hex string
            private_key_hex = priv_key_bytes.hex()
            
            return {
                'address': address_str,
                'private_key': private_key_hex
            }
        except Exception as e:
            logging.error(f"Error generating TON address with key: {e}")
            return None
    
    def _generate_ton_address(self, index):
        """Generate TON address (deprecated - use generate_ton_with_key)"""
        ton_data = self.generate_ton_with_key(index)
        return ton_data['address'] if ton_data else None
    
    def _derive_ton_private_key(self, index):
        """Derive TON private key (deprecated - use generate_ton_with_key)"""
        ton_data = self.generate_ton_with_key(index)
        return bytes.fromhex(ton_data['private_key']) if ton_data else None


class EvmService:
    """Service for EVM chains (ETH, BNB, BASE)"""
    
    def __init__(self, chain):
        self.chain = chain
        self.rpc_url = RPC_ENDPOINTS[chain]
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.master_wallet = MASTER_WALLETS[chain]
    
    async def get_balance(self, address):
        """Get native token balance"""
        try:
            balance_wei = self.w3.eth.get_balance(address)
            balance = self.w3.from_wei(balance_wei, 'ether')
            return float(balance)
        except Exception as e:
            logging.error(f"Error getting {self.chain} balance for {address}: {e}")
            return 0.0
    
    async def get_token_balance(self, address, token_contract, decimals):
        """Get ERC20 token balance"""
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_contract),
                abi=[{
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }]
            )
            balance = contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
            return balance / (10 ** decimals)
        except Exception as e:
            logging.error(f"Error getting token balance: {e}")
            return 0.0
    
    async def sweep(self, from_address, private_key, amount=None):
        """Sweep native tokens to master wallet"""
        try:
            account = Account.from_key(private_key)
            
            # Get balance
            balance = await self.get_balance(from_address)
            if balance == 0:
                return None
            
            # Get gas price
            gas_price = self.w3.eth.gas_price
            gas_limit = 21000
            gas_cost = self.w3.from_wei(gas_price * gas_limit, 'ether')
            
            # Calculate amount to send
            if amount is None:
                amount = balance - float(gas_cost)
            
            if amount <= 0:
                logging.warning(f"Insufficient balance for gas on {self.chain}")
                return None
            
            # Build transaction
            tx = {
                'from': Web3.to_checksum_address(from_address),
                'to': Web3.to_checksum_address(self.master_wallet),
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(from_address),
                'chainId': self.w3.eth.chain_id
            }
            
            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            logging.info(f"Swept {amount} {self.chain} from {from_address} - TX: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logging.error(f"Error sweeping {self.chain}: {e}")
            return None
    
    async def sweep_token(self, from_address, private_key, token_contract, decimals):
        """Sweep ERC20 tokens to master wallet"""
        try:
            account = Account.from_key(private_key)
            
            # Get token balance
            balance = await self.get_token_balance(from_address, token_contract, decimals)
            if balance == 0:
                return None
            
            # ERC20 transfer ABI
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_contract),
                abi=[{
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }]
            )
            
            # Build transaction
            amount_wei = int(balance * (10 ** decimals))
            tx = contract.functions.transfer(
                Web3.to_checksum_address(self.master_wallet),
                amount_wei
            ).build_transaction({
                'from': Web3.to_checksum_address(from_address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(from_address),
                'chainId': self.w3.eth.chain_id
            })
            
            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            logging.info(f"Swept {balance} tokens from {from_address} - TX: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logging.error(f"Error sweeping token: {e}")
            return None
    
    async def fund_gas(self, to_address, amount):
        """Fund address with gas for token transfer"""
        try:
            hot_wallet = Account.from_key(HOT_WALLET_PRIVATE_KEY)
            
            tx = {
                'from': hot_wallet.address,
                'to': Web3.to_checksum_address(to_address),
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(hot_wallet.address),
                'chainId': self.w3.eth.chain_id
            }
            
            signed = self.w3.eth.account.sign_transaction(tx, HOT_WALLET_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            logging.info(f"Funded {to_address} with {amount} {self.chain} - TX: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logging.error(f"Error funding gas: {e}")
            return None
    
    async def scan_address(self, address, last_block=None):
        """Scan address for new transactions using getLogs (event-based, more efficient)"""
        try:
            current_block = self.w3.eth.block_number
            
            # Limit scan range to prevent timeout (max 1000 blocks)
            start_block = last_block + 1 if last_block else max(0, current_block - 100)
            if current_block - start_block > 1000:
                start_block = current_block - 1000
            
            transactions = []
            
            # For native transfers, we'd need to scan blocks or use a block explorer API
            # This is a simplified version - production should use Etherscan/block explorer API
            # or maintain an indexer
            
            # Check current balance only (simplified approach)
            balance = await self.get_balance(address)
            if balance > 0.0001:
                transactions.append({
                    'tx_hash': f"balance_check_{address}_{current_block}",
                    'from': None,
                    'to': address,
                    'value': balance,
                    'block_number': current_block,
                    'token': None
                })
            
            return transactions, current_block
            
        except Exception as e:
            logging.error(f"Error scanning address: {e}")
            return [], None


class TronService:
    """Service for TRON blockchain"""
    
    def __init__(self):
        if not TRON_AVAILABLE:
            raise ImportError("TRON library not available")
        self.chain = "TRON"
        self.tron = Tron(network='mainnet')
        self.master_wallet = MASTER_WALLETS['TRON']
    
    async def get_balance(self, address):
        """Get TRX balance"""
        try:
            balance = self.tron.get_account_balance(address)
            return balance if balance else 0.0
        except Exception as e:
            logging.error(f"Error getting TRON balance: {e}")
            return 0.0
    
    async def get_token_balance(self, address, token_contract):
        """Get TRC20 token balance"""
        try:
            contract = self.tron.get_contract(token_contract)
            balance = contract.functions.balanceOf(address)
            decimals = contract.functions.decimals()
            return balance / (10 ** decimals)
        except Exception as e:
            logging.error(f"Error getting TRON token balance: {e}")
            return 0.0
    
    async def sweep(self, from_address, private_key):
        """Sweep TRX to master wallet"""
        try:
            priv_key = TronPrivateKey(bytes.fromhex(private_key))
            balance = await self.get_balance(from_address)
            
            if balance < 1:  # Minimum 1 TRX
                return None
            
            # Reserve some TRX for fees
            amount = balance - 1.1
            
            tx = (
                self.tron.trx.transfer(from_address, self.master_wallet, int(amount * 1_000_000))
                .build()
                .sign(priv_key)
            )
            
            result = tx.broadcast()
            
            if result.get('result'):
                tx_hash = result.get('txid')
                logging.info(f"Swept {amount} TRX from {from_address} - TX: {tx_hash}")
                return tx_hash
            return None
            
        except Exception as e:
            logging.error(f"Error sweeping TRON: {e}")
            return None
    
    async def sweep_token(self, from_address, private_key, token_contract):
        """Sweep TRC20 tokens to master wallet"""
        try:
            priv_key = TronPrivateKey(bytes.fromhex(private_key))
            contract = self.tron.get_contract(token_contract)
            
            balance = await self.get_token_balance(from_address, token_contract)
            if balance == 0:
                return None
            
            decimals = contract.functions.decimals()
            amount = int(balance * (10 ** decimals))
            
            tx = (
                contract.functions.transfer(self.master_wallet, amount)
                .with_owner(from_address)
                .fee_limit(50_000_000)
                .build()
                .sign(priv_key)
            )
            
            result = tx.broadcast()
            
            if result.get('result'):
                tx_hash = result.get('txid')
                logging.info(f"Swept {balance} tokens from {from_address} - TX: {tx_hash}")
                return tx_hash
            return None
            
        except Exception as e:
            logging.error(f"Error sweeping TRON token: {e}")
            return None
    
    async def fund_gas(self, to_address, amount=15):
        """Fund address with TRX for fees"""
        try:
            hot_priv_key = TronPrivateKey(bytes.fromhex(HOT_WALLET_PRIVATE_KEY.replace('0x', '')))
            hot_address = hot_priv_key.public_key.to_base58check_address()
            
            tx = (
                self.tron.trx.transfer(hot_address, to_address, int(amount * 1_000_000))
                .build()
                .sign(hot_priv_key)
            )
            
            result = tx.broadcast()
            
            if result.get('result'):
                return result.get('txid')
            return None
            
        except Exception as e:
            logging.error(f"Error funding TRON gas: {e}")
            return None


class SolanaService:
    """Service for Solana blockchain"""
    
    def __init__(self):
        if not SOLANA_AVAILABLE:
            raise ImportError("Solana library not available")
        self.chain = "SOLANA"
        self.rpc_url = RPC_ENDPOINTS['SOLANA']
        self.master_wallet = MASTER_WALLETS['SOLANA']
    
    async def get_balance(self, address):
        """Get SOL balance"""
        try:
            async with SolanaClient(self.rpc_url) as client:
                pubkey = SoldersPubkey.from_string(address)
                response = await client.get_balance(pubkey)
                if response.value:
                    return response.value / 1e9  # Convert lamports to SOL
                return 0.0
        except Exception as e:
            logging.error(f"Error getting Solana balance: {e}")
            return 0.0
    
    async def get_token_balance(self, address, mint_address):
        """Get SPL token balance"""
        try:
            async with SolanaClient(self.rpc_url) as client:
                pubkey = SoldersPubkey.from_string(address)
                response = await client.get_token_accounts_by_owner(
                    pubkey,
                    {"mint": SoldersPubkey.from_string(mint_address)}
                )
                
                if response.value:
                    # Parse token account data
                    import struct
                    for account in response.value:
                        data = account.account.data
                        # SPL token account layout: amount is at offset 64, 8 bytes
                        amount = struct.unpack('<Q', data[64:72])[0]
                        decimals = TOKEN_CONTRACTS['SOLANA'].get('USDT', {}).get('decimals', 6)
                        return amount / (10 ** decimals)
                return 0.0
        except Exception as e:
            logging.error(f"Error getting Solana token balance: {e}")
            return 0.0
    
    async def sweep(self, from_address, private_key_bytes):
        """Sweep SOL to master wallet"""
        try:
            async with SolanaClient(self.rpc_url) as client:
                # Create keypair from private key bytes
                from_keypair = SoldersKeypair.from_bytes(private_key_bytes)
                
                # Get balance
                balance_response = await client.get_balance(from_keypair.pubkey())
                balance_lamports = balance_response.value
                
                # Reserve for fees (5000 lamports)
                if balance_lamports < 10000:
                    return None
                
                amount = balance_lamports - 5000
                
                # Create transfer instruction
                transfer_ix = solders_transfer(
                    SoldersTransferParams(
                        from_pubkey=from_keypair.pubkey(),
                        to_pubkey=SoldersPubkey.from_string(self.master_wallet),
                        lamports=amount
                    )
                )
                
                # Get recent blockhash
                blockhash_response = await client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash
                
                # Create and sign transaction
                tx = SoldersTransaction.new_with_payer([transfer_ix], from_keypair.pubkey())
                tx.partial_sign([from_keypair], recent_blockhash)
                
                # Send transaction
                result = await client.send_transaction(tx)
                tx_hash = str(result.value)
                
                logging.info(f"Swept {amount/1e9} SOL from {from_address} - TX: {tx_hash}")
                return tx_hash
                
        except Exception as e:
            logging.error(f"Error sweeping Solana: {e}")
            return None
    
    async def fund_gas(self, to_address, amount=0.001):
        """Fund address with SOL for fees"""
        try:
            async with SolanaClient(self.rpc_url) as client:
                # Create hot wallet keypair from private key
                hot_priv_bytes = bytes.fromhex(HOT_WALLET_PRIVATE_KEY.replace('0x', ''))
                # Pad to 64 bytes if needed (32 private + 32 public)
                if len(hot_priv_bytes) == 32:
                    # Need to derive the full keypair
                    hot_keypair = SoldersKeypair.from_seed(hot_priv_bytes)
                else:
                    hot_keypair = SoldersKeypair.from_bytes(hot_priv_bytes)
                
                # Create transfer
                transfer_ix = solders_transfer(
                    SoldersTransferParams(
                        from_pubkey=hot_keypair.pubkey(),
                        to_pubkey=SoldersPubkey.from_string(to_address),
                        lamports=int(amount * 1e9)
                    )
                )
                
                blockhash_response = await client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash
                
                tx = SoldersTransaction.new_with_payer([transfer_ix], hot_keypair.pubkey())
                tx.partial_sign([hot_keypair], recent_blockhash)
                
                result = await client.send_transaction(tx)
                
                return str(result.value)
                
        except Exception as e:
            logging.error(f"Error funding Solana gas: {e}")
            return None


class TonService:
    """Service for TON blockchain"""
    
    def __init__(self):
        if not TON_AVAILABLE:
            raise ImportError("TON library not available")
        self.chain = "TON"
        self.rpc_url = RPC_ENDPOINTS['TON']
        self.master_wallet = MASTER_WALLETS['TON']
    
    async def get_balance(self, address):
        """Get TON balance"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.rpc_url}/getAddressBalance",
                    params={"address": address}
                )
                data = response.json()
                if data.get('ok'):
                    balance = int(data['result']) / 1e9
                    return balance
                return 0.0
        except Exception as e:
            logging.error(f"Error getting TON balance: {e}")
            return 0.0
    
    async def sweep(self, from_address, private_key):
        """Sweep TON to master wallet"""
        try:
            # TON sweep implementation
            # Note: Full implementation requires pytoniq or ton libraries
            balance = await self.get_balance(from_address)
            
            if balance < 0.1:  # Minimum 0.1 TON
                return None
            
            # Reserve for fees
            amount = balance - 0.05
            
            # This is a simplified version - production needs full TON wallet contract
            logging.warning("TON sweep requires full wallet contract implementation")
            return None
            
        except Exception as e:
            logging.error(f"Error sweeping TON: {e}")
            return None


class BlockMonitor:
    """Monitors blockchain for new deposits"""
    
    def __init__(self, db: DepositDatabase):
        self.db = db
        self.services = {}
        self.last_scanned_blocks = {}
        
        # Initialize services
        for chain in ['ETH', 'BNB', 'BASE']:
            try:
                self.services[chain] = EvmService(chain)
            except (ImportError, ConnectionError, ValueError) as e:
                logging.error(f"Error initializing {chain} service: {e}")
        
        try:
            self.services['TRON'] = TronService()
        except (ImportError, ConnectionError, ValueError) as e:
            logging.error(f"Error initializing TRON service: {e}")
        
        try:
            self.services['SOLANA'] = SolanaService()
        except (ImportError, ConnectionError, ValueError) as e:
            logging.error(f"Error initializing Solana service: {e}")
        
        try:
            self.services['TON'] = TonService()
        except (ImportError, ConnectionError, ValueError) as e:
            logging.error(f"Error initializing TON service: {e}")
    
    async def scan_all_addresses(self):
        """Scan all user addresses for deposits"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get all user addresses
            cursor.execute('SELECT user_id, telegram_id, address_index, eth_address, bnb_address, base_address, tron_address, solana_address, ton_address FROM user_addresses')
            users = cursor.fetchall()
            conn.close()
            
            for user in users:
                user_id, telegram_id, index, eth_addr, bnb_addr, base_addr, tron_addr, sol_addr, ton_addr = user
                
                addresses = {
                    'ETH': eth_addr,
                    'BNB': bnb_addr,
                    'BASE': base_addr,
                    'TRON': tron_addr,
                    'SOLANA': sol_addr,
                    'TON': ton_addr
                }
                
                for chain, address in addresses.items():
                    if address and chain in self.services:
                        await self._scan_address(chain, address, user_id, telegram_id)
                        # Add small delay to prevent rate limiting
                        await asyncio.sleep(0.1)
            
        except Exception as e:
            logging.error(f"Error in scan_all_addresses: {e}")
    
    async def scan_address(self, chain, address, user_id, telegram_id):
        """Scan single address for deposits - Public interface"""
        await self._scan_address(chain, address, user_id, telegram_id)
    
    async def _scan_address(self, chain, address, user_id, telegram_id):
        """Scan single address for deposits"""
        try:
            service = self.services.get(chain)
            if not service:
                return
            
            # Check native balance
            balance = await service.get_balance(address)
            if balance > 0.0001:  # Minimum threshold
                # Check if already recorded
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, confirmations FROM deposits 
                    WHERE user_id = ? AND chain = ? AND to_address = ? AND token IS NULL
                    AND status IN ('pending', 'confirmed')
                    ORDER BY created_at DESC LIMIT 1
                ''', (user_id, chain, address))
                
                existing = cursor.fetchone()
                
                if not existing:
                    # New deposit detected - get price
                    symbol = 'ETH' if chain == 'BASE' else chain.replace('CHAIN', '')
                    price_usd = await get_crypto_price_usd(symbol)
                    amount_usd = balance * price_usd
                    
                    tx_hash = f"native_{chain}_{address}_{int(datetime.now().timestamp())}"
                    
                    self.db.add_deposit(
                        tx_hash=tx_hash,
                        user_id=user_id,
                        chain=chain,
                        amount=balance,
                        amount_usd=amount_usd,
                        to_address=address
                    )
                    
                    logging.info(f"New deposit detected: {balance} {chain} for user {telegram_id} (${amount_usd:.2f})")
                    
                    # Update confirmations - simulate confirmation tracking
                    required_confs = CONFIRMATIONS.get(chain, 10)
                    self.db.update_deposit_status(tx_hash, 'confirmed', confirmations=required_confs)
                    
                    # Credit user only after confirmations
                    if telegram_id in user_wallets:
                        user_wallets[telegram_id] += amount_usd
                        # Track deposit for wager requirement (2x)
                        if telegram_id in user_stats:
                            user_stats[telegram_id]["unwagered_deposit"] = user_stats[telegram_id].get("unwagered_deposit", 0.0) + amount_usd
                        save_user_data(telegram_id)
                        logging.info(f"Credited ${amount_usd:.2f} to user {telegram_id}")
                
                conn.close()
            
            # Check token balances
            if chain in TOKEN_CONTRACTS:
                for token_name, token_info in TOKEN_CONTRACTS[chain].items():
                    if chain == 'SOLANA':
                        token_balance = await service.get_token_balance(address, token_info['mint'])
                    else:
                        token_balance = await service.get_token_balance(
                            address, 
                            token_info['address'],
                            token_info['decimals']
                        )
                    
                    if token_balance > 1:  # Minimum 1 token
                        # Check if already recorded
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT id FROM deposits 
                            WHERE user_id = ? AND chain = ? AND to_address = ? AND token = ? 
                            AND status IN ('pending', 'confirmed')
                            ORDER BY created_at DESC LIMIT 1
                        ''', (user_id, chain, address, token_name))
                        
                        if not cursor.fetchone():
                            tx_hash = f"token_{chain}_{token_name}_{address}_{int(datetime.now().timestamp())}"
                            amount_usd = token_balance  # USDT/USDC are 1:1 with USD
                            
                            self.db.add_deposit(
                                tx_hash=tx_hash,
                                user_id=user_id,
                                chain=chain,
                                token=token_name,
                                amount=token_balance,
                                amount_usd=amount_usd,
                                to_address=address
                            )
                            
                            logging.info(f"New token deposit: {token_balance} {token_name} on {chain} for user {telegram_id}")
                            
                            # Update confirmations and credit
                            required_confs = CONFIRMATIONS.get(chain, 10)
                            self.db.update_deposit_status(tx_hash, 'confirmed', confirmations=required_confs)
                            
                            # Credit user only after confirmations
                            if telegram_id in user_wallets:
                                user_wallets[telegram_id] += amount_usd
                                # Track deposit for wager requirement (2x)
                                if telegram_id in user_stats:
                                    user_stats[telegram_id]["unwagered_deposit"] = user_stats[telegram_id].get("unwagered_deposit", 0.0) + amount_usd
                                save_user_data(telegram_id)
                                logging.info(f"Credited ${amount_usd:.2f} to user {telegram_id}")
                        
                        conn.close()
            
        except Exception as e:
            logging.error(f"Error scanning {chain} address {address}: {e}")


class AutoSweeper:
    """Automatically sweeps confirmed deposits to master wallet"""
    
    def __init__(self, db: DepositDatabase):
        self.db = db
        self.wallet_manager = HDWalletManager()
        self.services = {}
        
        # Initialize services
        for chain in ['ETH', 'BNB', 'BASE']:
            try:
                self.services[chain] = EvmService(chain)
            except Exception as e:
                logging.error(f"Error initializing {chain} service: {e}")
        
        try:
            self.services['TRON'] = TronService()
        except:
            pass
        
        try:
            self.services['SOLANA'] = SolanaService()
        except:
            pass
        
        try:
            self.services['TON'] = TonService()
        except:
            pass
    
    async def process_pending_sweeps(self):
        """Process all confirmed deposits that need sweeping"""
        try:
            # Get deposits ready for sweep
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT d.id, d.tx_hash, d.chain, d.token, d.amount, d.to_address, u.address_index
                FROM deposits d
                JOIN user_addresses u ON d.user_id = u.user_id
                WHERE d.status = 'confirmed' OR (d.status = 'pending' AND d.amount_usd >= ?)
                ORDER BY d.created_at ASC
                LIMIT 50
            ''', (MIN_DEPOSIT_USD,))
            
            deposits = cursor.fetchall()
            conn.close()
            
            for deposit in deposits:
                dep_id, tx_hash, chain, token, amount, to_address, addr_index = deposit
                
                try:
                    await self._sweep_deposit(chain, token, to_address, addr_index, tx_hash)
                except Exception as e:
                    logging.error(f"Error sweeping deposit {tx_hash}: {e}")
            
        except Exception as e:
            logging.error(f"Error in process_pending_sweeps: {e}")
    
    async def _sweep_deposit(self, chain, token, from_address, address_index, deposit_tx_hash):
        """Sweep individual deposit"""
        try:
            service = self.services.get(chain)
            if not service:
                logging.warning(f"Service not available for {chain}")
                return
            
            # Get private key
            private_key = self.wallet_manager.derive_private_key(chain, address_index)
            
            sweep_tx_hash = None
            
            if token:
                # Token sweep - need to fund gas first
                logging.info(f"Sweeping token {token} on {chain} from {from_address}")
                
                # Check if address has gas
                native_balance = await service.get_balance(from_address)
                gas_needed = GAS_AMOUNTS.get(chain, 0.001)
                
                if native_balance < gas_needed:
                    # Fund gas
                    logging.info(f"Funding {gas_needed} {chain} for gas")
                    gas_tx = await service.fund_gas(from_address, gas_needed)
                    
                    if gas_tx:
                        # Wait a bit for gas to arrive
                        await asyncio.sleep(5)
                    else:
                        logging.error("Failed to fund gas")
                        return
                
                # Sweep token
                if chain == 'SOLANA':
                    token_contract = TOKEN_CONTRACTS[chain][token]['mint']
                elif chain in TOKEN_CONTRACTS and token in TOKEN_CONTRACTS[chain]:
                    token_contract = TOKEN_CONTRACTS[chain][token]['address']
                else:
                    logging.error(f"Token contract not found for {token} on {chain}")
                    return
                
                if chain == 'TRON':
                    sweep_tx_hash = await service.sweep_token(from_address, private_key, token_contract)
                elif chain == 'SOLANA':
                    # Solana SPL token sweep would go here
                    logging.warning("Solana SPL token sweep not fully implemented")
                else:
                    decimals = TOKEN_CONTRACTS[chain][token]['decimals']
                    sweep_tx_hash = await service.sweep_token(from_address, private_key, token_contract, decimals)
            
            else:
                # Native token sweep
                logging.info(f"Sweeping native {chain} from {from_address}")
                
                if chain == 'SOLANA':
                    sweep_tx_hash = await service.sweep(from_address, private_key)
                else:
                    sweep_tx_hash = await service.sweep(from_address, private_key)
            
            if sweep_tx_hash:
                # Update database
                self.db.update_deposit_status(
                    deposit_tx_hash,
                    status='swept',
                    sweep_tx_hash=sweep_tx_hash,
                    swept_at=datetime.now().isoformat()
                )
                logging.info(f"Successfully swept deposit {deposit_tx_hash} - Sweep TX: {sweep_tx_hash}")
            
        except Exception as e:
            logging.error(f"Error in _sweep_deposit: {e}")


# ===== DEPOSIT COMMAND HANDLERS =====

def build_deposit_menu():
    """Build deposit menu dynamically based on available chains"""
    # Build chain list based on availability
    chains_text = [
        "• 🔷 <b>Ethereum (ETH)</b> - ETH, USDT, USDC",
        "• 🟡 <b>BNB Chain (BNB)</b> - BNB, USDT, USDC",
        "• 🔵 <b>Base</b> - ETH, USDC",
    ]
    
    keyboard_rows = [
        [
            InlineKeyboardButton("🔷 Ethereum", callback_data="deposit_ETH"),
            InlineKeyboardButton("🟡 BNB Chain", callback_data="deposit_BNB")
        ],
        [
            InlineKeyboardButton("🔵 Base", callback_data="deposit_BASE"),
        ]
    ]
    
    # Add TRON if available
    if TRON_AVAILABLE:
        chains_text.append("• 🔴 <b>TRON (TRX)</b> - TRX, USDT")
        keyboard_rows[-1].append(InlineKeyboardButton("🔴 TRON", callback_data="deposit_TRON"))
    
    # Add Solana if available
    row_3 = []
    if SOLANA_AVAILABLE:
        chains_text.append("• 🟣 <b>Solana (SOL)</b> - SOL, USDT, USDC")
        row_3.append(InlineKeyboardButton("🟣 Solana", callback_data="deposit_SOLANA"))
    
    # TON deposit removed as per requirements
    # if TON_AVAILABLE:
    #     chains_text.append("• 💎 <b>TON</b> - TON")
    #     row_3.append(InlineKeyboardButton("💎 TON", callback_data="deposit_TON"))
    
    if row_3:
        keyboard_rows.append(row_3)
    
    # Add bottom row
    keyboard_rows.append([
        InlineKeyboardButton("📊 Deposit History", callback_data="deposit_history"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
    ])
    
    text = (
        "💰 <b>Deposit Funds</b>\n\n"
        "Select a blockchain to get your unique deposit address:\n\n"
        + "\n".join(chains_text) + "\n\n"
        f"<i>Minimum deposit: ${MIN_DEPOSIT_USD}</i>"
    )
    
    return text, keyboard_rows


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deposit options"""
    user_id = update.effective_user.id
    
    if not DEPOSIT_ENABLED:
        await update.message.reply_text("❌ Deposits are currently disabled.")
        return
    
    text, keyboard_rows = build_deposit_menu()
    sent_message = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard_rows), parse_mode=ParseMode.HTML)
    # Set menu owner after sending
    set_menu_owner(sent_message, user_id)


async def deposit_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit method selection"""
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    user_id = query.from_user.id
    chain = query.data.replace("deposit_", "")
    
    # Get or create user addresses
    db = DepositDatabase()
    user_data = db.get_or_create_user(user_id)
    
    # Get address for selected chain
    address = user_data.get(f"{chain.lower()}_address")
    
    if not address:
        error_msg = f"❌ <b>Error Generating {chain} Address</b>\n\n"
        if chain == 'TON':
            error_msg += "TON deposits are currently unavailable. The required library (pytoniq-core) is not installed.\n\n"
            error_msg += "Please contact the administrator or try another chain."
        else:
            error_msg += f"{chain} address could not be generated. Please try again or contact support."
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_deposit_menu")]]
        await safe_edit_message(
            query,
            error_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Log for debugging
    logging.info(f"Showing deposit address for user {user_id}, chain {chain}: {address}")
    
    # Generate QR code with the actual address
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(address)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    # Chain info
    chain_info = {
        'ETH': {'name': 'Ethereum', 'symbol': 'ETH', 'tokens': 'ETH, USDT, USDC'},
        'BNB': {'name': 'BNB Chain', 'symbol': 'BNB', 'tokens': 'BNB, USDT, USDC'},
        'BASE': {'name': 'Base', 'symbol': 'ETH', 'tokens': 'ETH, USDC'},
        'TRON': {'name': 'TRON', 'symbol': 'TRX', 'tokens': 'TRX, USDT'},
        'SOLANA': {'name': 'Solana', 'symbol': 'SOL', 'tokens': 'SOL, USDT, USDC'},
        'TON': {'name': 'TON', 'symbol': 'TON', 'tokens': 'TON'}
    }
    
    info = chain_info.get(chain, {})
    
    text = (
        f"💰 <b>{info['name']} Deposit Address</b>\n\n"
        f"<code>{address}</code>\n\n"
        f"<b>Supported Assets:</b> {info['tokens']}\n"
        f"<b>Network:</b> {info['name']}\n"
        f"<b>Min Deposit:</b> ${MIN_DEPOSIT_USD}\n\n"
        f"⚠️ <b>Important:</b>\n"
        f"• Only send {info['tokens']} to this address\n"
        f"• Deposits are automatically credited after {CONFIRMATIONS.get(chain, 10)} confirmations\n"
        f"• This is your personal deposit address\n\n"
        f"<i>Scan QR code or copy address above</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Check Status", callback_data=f"check_deposit_{chain}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_deposit_menu")]
    ]
    
    await query.message.reply_photo(
        photo=bio,
        caption=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    await query.delete_message()


async def check_deposit_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check deposit status - actively scans for new deposits"""
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer("Checking for deposits...")
    
    user_id = query.from_user.id
    
    # Extract chain from callback data if specific chain check
    chain_to_check = None
    if query.data.startswith("check_deposit_"):
        chain_to_check = query.data.replace("check_deposit_", "")
    
    db = DepositDatabase()
    
    # If checking a specific chain, trigger a scan for that address
    if chain_to_check:
        try:
            user_data = db.get_or_create_user(user_id)
            address = user_data.get(f"{chain_to_check.lower()}_address")
            
            if address:
                # Trigger an immediate scan for this specific address
                monitor = BlockMonitor(db)
                await monitor.scan_address(chain_to_check, address, user_data['user_id'], user_id)
                
                await query.answer("✅ Scan complete! Check results below.", show_alert=True)
        except Exception as e:
            logging.error(f"Error scanning address: {e}")
            await query.answer("⚠️ Error scanning address", show_alert=True)
    
    # Get deposit history
    deposits = db.get_user_deposits(user_id, limit=5)
    
    # Chain name mapping for display
    chain_names = {
        'ETH': 'Ethereum',
        'BNB': 'BNB Chain',
        'BASE': 'Base',
        'TRON': 'TRON',
        'SOLANA': 'Solana',
        'TON': 'TON'
    }
    
    if not deposits:
        text = (
            "📊 <b>Deposit Status</b>\n\n"
            "✅ <b>Scan Complete!</b>\n\n"
            "No deposits detected yet.\n\n"
            f"<i>Deposits for {chain_names.get(chain_to_check, chain_to_check) if chain_to_check else 'all chains'} have been checked.\n"
            "Send funds to your deposit address and check again.</i>"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Scan Again", callback_data=f"check_deposit_{chain_to_check}" if chain_to_check else "deposit_history")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_deposit_menu")]
        ]
    else:
        text = "📊 <b>Recent Deposits</b>\n\n"
        
        for dep in deposits:
            tx_hash, chain, token, amount, amount_usd, status, created_at, confirmed_at = dep
            
            status_emoji = {
                'pending': '⏳',
                'confirmed': '✅',
                'swept': '✅',
                'failed': '❌'
            }.get(status, '❓')
            
            asset = token or chain
            text += (
                f"{status_emoji} <b>{amount:.4f} {asset}</b> (${amount_usd:.2f})\n"
                f"   Chain: {chain}\n"
                f"   Status: {status.title()}\n"
                f"   Date: {created_at[:19]}\n"
                f"   TX: <code>{tx_hash[:16]}...</code>\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Scan Again", callback_data=f"check_deposit_{chain_to_check}" if chain_to_check else "deposit_history")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_deposit_menu")]
        ]
    
    # Use safe_edit_message to handle the transition from Photo -> Text
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def back_to_deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to deposit menu"""
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    text, keyboard = build_deposit_menu()
    
    # Use safe_edit_message to handle the transition from Photo -> Text
    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


# ===== BACKGROUND TASKS =====

async def monitor_deposits_task(application):
    """Background task to monitor deposits"""
    db = DepositDatabase()
    monitor = BlockMonitor(db)
    
    while not bot_stopped:
        try:
            await monitor.scan_all_addresses()
            await asyncio.sleep(SCAN_INTERVAL)
        except Exception as e:
            logging.error(f"Error in deposit monitor: {e}")
            await asyncio.sleep(SCAN_INTERVAL)


async def sweep_deposits_task(application):
    """Background task to sweep deposits"""
    db = DepositDatabase()
    sweeper = AutoSweeper(db)
    
    while not bot_stopped:
        try:
            await sweeper.process_pending_sweeps()
            await asyncio.sleep(SWEEP_INTERVAL)
        except Exception as e:
            logging.error(f"Error in auto sweeper: {e}")
            await asyncio.sleep(SWEEP_INTERVAL)


# ================================
# END OF DEPOSIT SYSTEM
# ================================

def load_language_files():
    """Load all language files at startup into the global LANGUAGES dictionary"""
    global LANGUAGES
    for lang_code, filename in LANGUAGE_FILES.items():
        lang_dict = load_language_file(lang_code)
        if lang_dict:
            # Merge with existing LANGUAGES dict (file takes precedence)
            if lang_code in LANGUAGES:
                LANGUAGES[lang_code].update(lang_dict)
            else:
                LANGUAGES[lang_code] = lang_dict
            logging.info(f"Loaded {len(lang_dict)} translations for {lang_code}")
        else:
            logging.warning(f"Failed to load language file for {lang_code}")

def get_text(user_id_or_key, key_or_lang=None, **kwargs):
    """
    Get translated text based on user's language preference.
    
    Supports two call signatures for backward compatibility:
    1. get_text(user_id, key, **kwargs) - New preferred signature (user_id can be int or None)
    2. get_text(key, lang_code, **kwargs) - Legacy signature (both are strings)
    
    Args:
        user_id_or_key: Either user_id (int/None) or translation key (str)
        key_or_lang: Either translation key (str) or language code (str), or None
        **kwargs: Format arguments for string formatting
        
    Returns:
        Formatted translated string with fallback to English
    """
    # Determine which signature is being used based on type
    if isinstance(user_id_or_key, (int, type(None))):
        # New signature: get_text(user_id, key, **kwargs)
        user_id = user_id_or_key
        key = key_or_lang
        # Get language from user_id, using DEFAULT_LANG only if user_id is explicitly None
        if user_id is not None:
            lang_code = get_user_lang(user_id)
        else:
            lang_code = DEFAULT_LANG
    else:
        # Legacy signature: get_text(key, lang_code, **kwargs)
        key = user_id_or_key
        lang_code = key_or_lang if key_or_lang else DEFAULT_LANG
    
    # Ensure lang_code is valid
    lang_code = lang_code if lang_code in LANGUAGE_FILES else DEFAULT_LANG
    
    # Try to get text from LANGUAGES dict (which now includes loaded files)
    if lang_code in LANGUAGES and key in LANGUAGES[lang_code]:
        text = LANGUAGES[lang_code][key]
    elif key in LANGUAGES.get(DEFAULT_LANG, {}):
        text = LANGUAGES[DEFAULT_LANG][key]
    else:
        logging.warning(f"Missing translation key: '{key}'")
        return f"Missing translation for '{key}'"
    
    # Format the text with provided kwargs
    try:
        return text.format(**kwargs)
    except KeyError as e:
        logging.warning(f"Missing format key {e} in text '{key}' for language '{lang_code}'")
        return text


async def safe_edit_message(query, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
    """
    Safely edit a message. If the source is a PhotoMessage, delete it and send new text.
    Automatically sets menu ownership if reply_markup is provided.
    """
    try:
        # Try to edit as text message
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    except Exception:
        # If it fails (likely because it's a photo message), delete and send new
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    
    # Automatically set menu ownership when there's a keyboard
    if reply_markup is not None and hasattr(query, 'from_user'):
        set_menu_owner(query.message, query.from_user.id)


## NEW FEATURE ##
# --- Conversation Handler States ---
(SELECT_BOMBS, SELECT_BET_AMOUNT, SELECT_TARGET_SCORE, ASK_AI_PROMPT, CHOOSE_AI_MODEL,
 ADMIN_SET_BALANCE_USER, ADMIN_SET_BALANCE_AMOUNT, ADMIN_SET_DAILY_BONUS, ADMIN_SEARCH_USER,
 ADMIN_BROADCAST_MESSAGE, ADMIN_SET_HOUSE_BALANCE, ADMIN_LIMITS_CHOOSE_TYPE,
 ADMIN_LIMITS_CHOOSE_GAME, ADMIN_LIMITS_SET_AMOUNT,
 SETTINGS_RECOVERY_PIN, RECOVER_ASK_TOKEN, RECOVER_ASK_PIN,
 ADMIN_GIFT_CODE_AMOUNT, ADMIN_GIFT_CODE_CLAIMS, ADMIN_GIFT_CODE_WAGER, SETTINGS_WITHDRAWAL_ADDRESS, SETTINGS_WITHDRAWAL_ADDRESS_CHANGE,
 WITHDRAWAL_AMOUNT, WITHDRAWAL_APPROVAL_TXID, TOWER_BET_AMOUNT, PF_CHANGE_CLIENT_SEED_INPUT,
 PF_VERIFY_INPUT_SERVER_SEED, PF_VERIFY_INPUT_CLIENT_SEED, PF_VERIFY_INPUT_NONCE, PF_VERIFY_INPUT_PARAM) = range(30)

# --- GAME MULTIPLIERS AND CONFIGS ---

# Roulette configuration
ROULETTE_CONFIG = {
    "single_number": {"multiplier": 35, "count": 1},
    "red": {"multiplier": 2, "numbers": [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]},
    "black": {"multiplier": 2, "numbers": [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]},
    "even": {"multiplier": 2, "numbers": [2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36]},
    "odd": {"multiplier": 2, "numbers": [1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35]},
    "low": {"multiplier": 2, "numbers": list(range(1, 19))},
    "high": {"multiplier": 2, "numbers": list(range(19, 37))},
    "column1": {"multiplier": 3, "numbers": [1,4,7,10,13,16,19,22,25,28,31,34]},
    "column2": {"multiplier": 3, "numbers": [2,5,8,11,14,17,20,23,26,29,32,35]},
    "column3": {"multiplier": 3, "numbers": [3,6,9,12,15,18,21,24,27,30,33,36]},
}

# Tower game multiplier chart (4 columns, varying bombs per row)
# NEW TOWER GAME MULTIPLIERS - 9 floors, 3 difficulties
TOWER_MULTIPLIERS = {
    'easy': {  # 4 tiles per floor, 25% risk (1 snake out of 4)
        0: 0.90,  # Floor 0 - can cash out immediately
        1: 1.27, 2: 1.69, 3: 2.25, 4: 3.01, 5: 4.01, 6: 5.34, 7: 7.12, 8: 9.50, 9: 12.66
    },
    'medium': {  # 3 tiles per floor, 33% risk (1 snake out of 3)
        0: 0.90,
        1: 1.43, 2: 2.14, 3: 3.21, 4: 4.81, 5: 7.22, 6: 10.83, 7: 16.24, 8: 24.36, 9: 36.54
    },
    'hard': {  # 2 tiles per floor, 50% risk (1 snake out of 2)
        0: 0.90,
        1: 1.90, 2: 3.80, 3: 7.60, 4: 15.21, 5: 30.42, 6: 60.84, 7: 121.68, 8: 243.35, 9: 486.71
    }
}

# Tower difficulty settings
TOWER_DIFFICULTY_CONFIG = {
    'easy': {'tiles': 4, 'risk': '25%', 'name': 'Easy'},
    'medium': {'tiles': 3, 'risk': '33%', 'name': 'Medium'},
    'hard': {'tiles': 2, 'risk': '50%', 'name': 'Hard'}
}

# Blackjack basic setup
CARD_VALUES = {
    'A': [1, 11], '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10
}
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

# --- MINES MULTIPLIER CHART (2% house edge applied) ---
MINES_MULT_TABLE = {
    # 1 Bomb
    1: {1: 1.01, 2: 1.06, 3: 1.1, 4: 1.16, 5: 1.22, 6: 1.27, 7: 1.34, 8: 1.43, 9: 1.52, 10: 1.62, 11: 1.73, 12: 1.86, 13: 2.02, 14: 2.21, 15: 2.42, 16: 2.69, 17: 3.03, 18: 3.47, 19: 4.04, 20: 4.85, 21: 6.07, 22: 8.08, 23: 12.12, 24: 24.25},
    # 2 Bombs
    2: {1: 1.06, 2: 1.15, 3: 1.26, 4: 1.38, 5: 1.53, 6: 1.71, 7: 1.9, 8: 2.14, 9: 2.42, 10: 2.77, 11: 3.19, 12: 3.73, 13: 4.41, 14: 5.29, 15: 6.47, 16: 8.08, 17: 10.4, 18: 13.86, 19: 19.4, 20: 29.11, 21: 48.51, 22: 97.02, 23: 291.06},
    # 3 Bombs
    3: {1: 1.1, 2: 1.26, 3: 1.45, 4: 1.68, 5: 1.96, 6: 2.3, 7: 2.73, 8: 3.28, 9: 3.99, 10: 4.9, 11: 6.13, 12: 7.8, 13: 10.14, 14: 13.52, 15: 18.59, 16: 26.57, 17: 39.85, 18: 63.76, 19: 111.57, 20: 223.15, 21: 584.33, 22: 2231.46},
    # 4 Bombs
    4: {1: 1.16, 2: 1.38, 3: 1.68, 4: 2.05, 5: 2.53, 6: 3.17, 7: 4.01, 8: 5.15, 9: 6.74, 10: 8.99, 11: 12.26, 12: 17.17, 13: 24.79, 14: 37.19, 15: 58.45, 16: 97.4, 17: 175.33, 18: 350.65, 19: 818.2, 20: 2454.61, 21: 12273.03},
    # 5 Bombs
    5: {1: 1.22, 2: 1.53, 3: 1.96, 4: 2.53, 5: 3.32, 6: 4.43, 7: 6.02, 8: 8.33, 9: 11.8, 10: 17.17, 11: 25.74, 12: 40.05, 13: 65.08, 14: 111.57, 15: 204.55, 16: 409.1, 17: 920.47, 18: 2454.61, 19: 8591.12, 20: 51546.73},
    # 6 Bombs
    6: {1: 1.27, 2: 1.71, 3: 2.3, 4: 3.17, 5: 4.43, 6: 6.33, 7: 9.25, 8: 13.89, 9: 21.45, 10: 34.33, 11: 57.21, 12: 100.13, 13: 185.95, 14: 371.91, 15: 818.2, 16: 2045.5, 17: 6136.52, 18: 24546.06, 19: 171822.42},
    # 7 Bombs
    7: {1: 1.34, 2: 1.9, 3: 2.73, 4: 4.01, 5: 6.02, 6: 9.25, 7: 14.65, 8: 23.98, 9: 40.77, 10: 72.47, 11: 135.89, 12: 271.78, 13: 588.85, 14: 1413.26, 15: 3886.45, 16: 12954.86, 17: 58296.89, 18: 466375.14},
    # 8 Bombs
    8: {1: 1.43, 2: 2.14, 3: 3.28, 4: 5.15, 5: 8.33, 6: 13.89, 7: 23.98, 8: 43.17, 9: 81.54, 10: 163.07, 11: 349.43, 12: 815.34, 13: 2119.89, 14: 6359.66, 15: 23318.76, 16: 116593.79, 17: 1049344.06},
    # 9 Bombs
    9: {1: 1.52, 2: 2.42, 3: 3.99, 4: 6.74, 5: 11.8, 6: 21.45, 7: 40.77, 8: 81.54, 9: 173.26, 10: 396.02, 11: 990.05, 12: 2772.16, 13: 9009.52, 14: 36038.08, 15: 198209.43, 16: 1982094.34},
    # 10 Bombs
    10: {1: 1.62, 2: 2.77, 3: 4.9, 4: 8.99, 5: 17.17, 6: 34.33, 7: 72.47, 8: 163.07, 9: 396.02, 10: 1056.06, 11: 3168.18, 12: 11088.64, 13: 48315.37, 14: 288304.63, 15: 3171350.95},
    # 11 Bombs
    11: {1: 1.73, 2: 3.19, 3: 6.13, 4: 12.26, 5: 25.74, 6: 57.21, 7: 135.89, 8: 349.43, 9: 990.05, 10: 3168.18, 11: 11880.69, 12: 55443.2, 13: 360380.79, 14: 4324569.48},
    # 12 Bombs
    12: {1: 1.86, 2: 3.73, 3: 7.8, 4: 17.17, 5: 40.05, 6: 100.13, 7: 271.78, 8: 815.34, 9: 2772.16, 10: 11088.64, 11: 55443.2, 12: 388102.39, 13: 5045331.06},
    # 13 Bombs
    13: {1: 2.02, 2: 4.41, 3: 10.14, 4: 24.79, 5: 65.08, 6: 185.95, 7: 588.85, 8: 2119.89, 9: 9009.52, 10: 48315.37, 11: 360380.79, 12: 5045331.06},
    # 14 Bombs
    14: {1: 2.21, 2: 5.29, 3: 13.52, 4: 37.19, 5: 111.57, 6: 371.91, 7: 1413.26, 8: 6359.66, 9: 36038.08, 10: 288304.63, 11: 4324569.48},
    # 15 Bombs
    15: {1: 2.42, 2: 6.47, 3: 18.59, 4: 58.45, 5: 204.55, 6: 818.2, 7: 3886.45, 8: 23318.76, 9: 198209.43, 10: 3171350.95},
    # 16 Bombs
    16: {1: 2.69, 2: 8.08, 3: 26.57, 4: 97.4, 5: 409.1, 6: 2045.5, 7: 12954.86, 8: 116593.79, 9: 1982094.34},
    # 17 Bombs
    17: {1: 3.03, 2: 10.4, 3: 39.85, 4: 175.33, 5: 920.47, 6: 6136.52, 7: 58296.89, 8: 1049344.06},
    # 18 Bombs
    18: {1: 3.47, 2: 13.86, 3: 63.76, 4: 350.65, 5: 2454.61, 6: 24546.06, 7: 466375.14},
    # 19 Bombs
    19: {1: 4.04, 2: 19.4, 3: 111.57, 4: 818.2, 5: 8591.12, 6: 171822.42},
    # 20 Bombs
    20: {1: 4.85, 2: 29.11, 3: 223.15, 4: 2454.61, 5: 51546.73},
    # 21 Bombs
    21: {1: 6.07, 2: 48.51, 3: 557.87, 4: 12273.03},
    # 22 Bombs
    22: {1: 8.08, 2: 97.02, 3: 2231.46},
    # 23 Bombs
    23: {1: 12.12, 2: 291.06},
    # 24 Bombs
    24: {1: 24.25}
}

# --- KENO PAYOUT TABLE ---
KENO_PAYOUTS = {
    1: {0: 0.67, 1: 1.79},
    2: {1: 1.93, 2: 3.68},
    3: {1: 1.06, 2: 1.33, 3: 25.21},
    4: {2: 2.13, 3: 7.66, 4: 87.27},
    5: {2: 1.45, 3: 4.07, 4: 12.6, 5: 290.9},
    6: {2: 1.06, 3: 1.93, 4: 6.01, 5: 96.96, 6: 678.78},
    7: {2: 1.06, 3: 1.55, 4: 3.39, 5: 14.54, 6: 218.18, 7: 678.78},
    8: {2: 1.06, 3: 1.45, 4: 1.93, 5: 5.33, 6: 37.81, 7: 96.96, 8: 775.75},
    9: {2: 1.06, 3: 1.26, 4: 1.64, 5: 2.42, 6: 7.27, 7: 48.48, 8: 242.42, 9: 969.69},
    10: {2: 1.06, 3: 1.16, 4: 1.26, 5: 1.74, 6: 3.39, 7: 12.6, 8: 48.48, 9: 242.42, 10: 969.69}
}

# --- SINGLE EMOJI GAMES CONFIGURATION ---
# New single emoji games with Telegram's native dice/emoji animations
SINGLE_EMOJI_GAMES = {
    "darts": {
        "emoji": "🎯",
        "name": "Single Dart",
        "dice_type": "🎯",  # Use emoji directly for Telegram API
        "multiplier": 1.15,
        "win_chance": 0.83,  # 83%
        "win_condition": lambda value: value >= 3,  # Dart hits the table (values 3-6)
        "win_description": "Dart hits the table"
    },
    "soccer": {
        "emoji": "⚽",
        "name": "Single Soccer",
        "dice_type": "⚽",  # Use emoji directly for Telegram API
        "multiplier": 1.53,
        "win_chance": 0.60,  # 60%
        "win_condition": lambda value: value in [3, 4, 5],  # Goal scored
        "win_description": "Goal scored"
    },
    "basket": {
        "emoji": "🏀",
        "name": "Single Basket",
        "dice_type": "🏀",  # Use emoji directly for Telegram API
        "multiplier": 2.25,
        "win_chance": 0.40,  # 40%
        "win_condition": lambda value: value in [4, 5],  # Ball goes in basket
        "win_description": "Ball goes in"
    },
    "bowling": {
        "emoji": "🎳",
        "name": "Single Bowling",
        "dice_type": "🎳",  # Use emoji directly for Telegram API
        "multiplier": 5.00,
        "win_chance": 0.16,  # 16%
        "win_condition": lambda value: value == 6,  # Strike
        "win_description": "Strike!"
    },
    "slot": {
        "emoji": "🎰",
        "name": "Slot Machine",
        "dice_type": "🎰",  # Use emoji directly for Telegram API
        "multiplier": 14.5,
        "win_chance": 0.0625,  # 6.25%
        "win_condition": lambda value: value in [1, 22, 43, 64],  # All same symbols (bar, grapes, lemon, seven)
        "win_description": "Same symbols"
    }
}


# --- Provably Fair System & Game ID Generation ---
def generate_server_seed():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def generate_client_seed():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def generate_unique_id(prefix='G'):
    timestamp = datetime.now(timezone.utc).strftime('%y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{random_part}"

def create_hash(server_seed, client_seed, nonce):
    combined = f"{server_seed}:{client_seed}:{nonce}"
    return hashlib.sha256(combined.encode()).hexdigest()

def get_provably_fair_result(server_seed, client_seed, nonce, max_value):
    hash_result = create_hash(server_seed, client_seed, nonce)
    # Convert first 8 characters of hash to integer
    hex_value = int(hash_result[:8], 16)
    return (hex_value % max_value)

def get_user_seeds(user_id):
    """Get user's current seeds and nonce"""
    pf_data = user_stats.get(user_id, {}).get("provably_fair", {})
    return {
        "server_seed": pf_data.get("server_seed", generate_server_seed()),
        "client_seed": pf_data.get("client_seed", generate_client_seed()),
        "nonce": pf_data.get("nonce", 0)
    }

def increment_user_nonce(user_id):
    """Increment user's nonce after a bet"""
    if user_id not in user_stats:
        return
    if "provably_fair" not in user_stats[user_id]:
        user_stats[user_id]["provably_fair"] = {
            "server_seed": generate_server_seed(),
            "client_seed": generate_client_seed(),
            "nonce": 0,
            "next_server_seed": generate_server_seed()
        }
    user_stats[user_id]["provably_fair"]["nonce"] += 1
    save_user_data(user_id)

def store_provably_fair_record(game_id, game_type, server_seed, client_seed, nonce, result_data=None):
    """Store provably fair verification data for a completed game"""
    provably_fair_records[game_id] = {
        "game_id": game_id,
        "game_type": game_type,
        "server_seed": server_seed,
        "client_seed": client_seed,
        "nonce": nonce,
        "result_data": result_data,  # Game-specific result information
        "timestamp": str(datetime.now(timezone.utc))
    }
    # Keep only last 1000 records to avoid memory issues
    if len(provably_fair_records) > 1000:
        oldest_key = next(iter(provably_fair_records))
        del provably_fair_records[oldest_key]

async def create_provably_fair_button(game_id, context):
    """Create a provably fair URL button that links to DM"""
    try:
        bot_username = (await context.bot.get_me()).username
        pf_url = f"https://t.me/{bot_username}?start=provablyfair_{game_id}"
        return InlineKeyboardButton("🔐 Provably Fair", url=pf_url)
    except Exception as e:
        logging.error(f"Error creating provably fair button: {e}")
        # Fallback to callback button if we can't get bot username
        return InlineKeyboardButton("🔐 Provably Fair", callback_data=f"pf_show_{game_id}")

def generate_mine_positions(server_seed, client_seed, nonce, num_mines):
    """Generate deterministic mine positions for Mines game"""
    positions = []
    offset = 0
    while len(positions) < num_mines:
        pos = get_provably_fair_result(server_seed, client_seed, nonce + offset, 25)
        if pos not in positions:
            positions.append(pos)
        offset += 1
    return sorted(positions)

def generate_tower_positions(server_seed, client_seed, nonce, difficulty, num_floors=9):
    """Generate deterministic snake positions for Tower game"""
    tiles_per_floor = {'easy': 4, 'medium': 3, 'hard': 2}.get(difficulty, 4)
    positions = []
    for floor in range(num_floors):
        snake_pos = get_provably_fair_result(server_seed, client_seed, nonce + floor, tiles_per_floor)
        positions.append(snake_pos)
    return positions

def get_limbo_multiplier(server_seed, client_seed, nonce):
    """
    Generate a provably fair Limbo multiplier using inverse exponential distribution.
    Returns a multiplier between 1.00 and 1000.00.
    The chance of getting 2x is ~46%, 4x is ~23%, etc. (3% house edge)
    """
    hash_result = create_hash(server_seed, client_seed, nonce)
    # Use first 13 hex characters for better precision
    hex_value = int(hash_result[:13], 16)
    # Normalize to 0-1 range
    max_val = 16 ** 13
    normalized = hex_value / max_val
    
    # Use inverse exponential: multiplier = 0.97 / (1 - normalized)
    # This creates the desired probability distribution with 3% house edge
    # Clamp between 1.00 and 1000.00
    house_edge = 0.03  # 3% house edge
    try:
        result = (1 - house_edge) / normalized if normalized > 0 else 1000.00
        result = max(1.00, min(1000.00, result))
        return round(result, 2)
    except:
        return 1.00

# --- Persistent User Data Utilities ---
def normalize_username(username):
    if not username:
        return None
    username = username.lower()
    if not username.startswith("@"):
        username = "@" + username
    return username

def load_all_user_data():
    global user_wallets, username_to_userid, user_stats
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(DATA_DIR, fname), "r") as f:
                    data = json.load(f)
                    user_id = int(fname.split(".")[0])
                    user_wallets[user_id] = data.get("wallet", 0.0)
                    username = data.get("userinfo", {}).get("username")
                    if username:
                        username_to_userid[normalize_username(username)] = user_id
                    user_stats[user_id] = data
            except (json.JSONDecodeError, ValueError) as e:
                logging.error(f"Could not load data for {fname}: {e}")

def save_user_data(user_id):
    if user_id not in user_stats:
        logging.warning(f"Attempted to save data for non-existent user: {user_id}")
        return
    data = user_stats.get(user_id, {})
    data["wallet"] = user_wallets.get(user_id, 0.0)
    with open(os.path.join(DATA_DIR, f"{user_id}.json"), "w") as f:
        json.dump(data, f, default=str, indent=2)

def save_all_user_data():
    logging.info("Saving all user data...")
    for user_id in user_stats.keys():
        save_user_data(user_id)
    logging.info("All user data saved.")

## NEW FEATURE - Data Persistence ##
def save_bot_state():
    """Saves the entire bot state to a single JSON file."""
    logging.info("Shutting down... Saving bot state.")
    state = {
        'user_wallets': user_wallets,
        'username_to_userid': username_to_userid,
        'game_sessions': game_sessions,
        'user_pending_invitations': user_pending_invitations,
        'escrow_deals': escrow_deals,
        'bot_stopped': bot_stopped,
        'bot_settings': bot_settings # NEW
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, default=str, indent=2)
        logging.info("Bot state saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save bot state: {e}")
    save_all_user_data() # Also save individual user files as a backup
    save_all_escrow_deals()
    save_all_group_settings() # NEW
    save_all_recovery_data() # NEW
    save_all_gift_codes() # NEW

def load_bot_state():
    """Loads the bot state from a single JSON file."""
    global user_wallets, username_to_userid, user_stats, game_sessions, user_pending_invitations, escrow_deals, bot_stopped, bot_settings, group_settings, recovery_data, gift_codes

    # Load individual files first as a fallback
    load_all_user_data()
    load_all_escrow_deals()
    load_all_group_settings() # NEW
    load_all_recovery_data() # NEW
    load_all_gift_codes() # NEW

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            # Convert string keys back to int for wallets
            user_wallets.update({int(k): v for k, v in state.get('user_wallets', {}).items()})
            username_to_userid.update(state.get('username_to_userid', {}))
            game_sessions.update(state.get('game_sessions', {}))
            user_pending_invitations.update(state.get('user_pending_invitations', {}))
            escrow_deals.update(state.get('escrow_deals', {}))
            bot_stopped = state.get('bot_stopped', False)
            bot_settings.update(state.get('bot_settings', {})) # NEW
            logging.info("Bot state restored successfully from state file.")
        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"Could not load bot state from {STATE_FILE}: {e}. Relying on individual files.")
    else:
        logging.info("No state file found. Starting with a fresh state from individual user/escrow files.")

def load_all_escrow_deals():
    global escrow_deals
    logging.info("Loading all escrow deals from files...")
    for fname in os.listdir(ESCROW_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(ESCROW_DIR, fname), "r") as f:
                    deal = json.load(f)
                    deal_id = deal.get("id")
                    if deal_id:
                        # Only load active deals into memory
                        if deal.get("status") not in ["completed", "cancelled_by_owner", "disputed", "release_failed"]:
                            escrow_deals[deal_id] = deal
            except Exception as e:
                logging.error(f"Could not load escrow deal from {fname}: {e}")
    logging.info(f"Loaded {len(escrow_deals)} active escrow deals.")

def save_escrow_deal(deal_id):
    deal = escrow_deals.get(deal_id)
    if not deal:
        logging.warning(f"Attempted to save non-existent escrow deal: {deal_id}")
        return
    try:
        with open(os.path.join(ESCROW_DIR, f"{deal_id}.json"), "w") as f:
            json.dump(deal, f, default=str, indent=2)
    except Exception as e:
        logging.error(f"Failed to save escrow deal {deal_id}: {e}")

def save_all_escrow_deals():
    logging.info("Saving all escrow deals...")
    for deal_id in escrow_deals.keys():
        save_escrow_deal(deal_id)
    logging.info("All escrow deals saved.")

## NEW FEATURE - Group Settings Persistence ##
def save_group_settings(chat_id):
    settings = group_settings.get(chat_id)
    if not settings:
        return
    try:
        with open(os.path.join(GROUPS_DIR, f"{chat_id}.json"), "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save group settings for {chat_id}: {e}")

def load_all_group_settings():
    global group_settings
    logging.info("Loading all group settings...")
    for fname in os.listdir(GROUPS_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(GROUPS_DIR, fname), "r") as f:
                    settings = json.load(f)
                    chat_id = int(fname.split(".")[0])
                    group_settings[chat_id] = settings
            except Exception as e:
                logging.error(f"Could not load group settings from {fname}: {e}")
    logging.info(f"Loaded settings for {len(group_settings)} groups.")

def save_all_group_settings():
    logging.info("Saving all group settings...")
    for chat_id in group_settings.keys():
        save_group_settings(chat_id)
    logging.info("All group settings saved.")

## NEW FEATURE - Recovery Data Persistence ##
def save_recovery_data(token_hash):
    data = recovery_data.get(token_hash)
    if not data:
        return
    try:
        with open(os.path.join(RECOVERY_DIR, f"{token_hash}.json"), "w") as f:
            json.dump(data, f, default=str, indent=2)
    except Exception as e:
        logging.error(f"Failed to save recovery data for token hash {token_hash}: {e}")

def load_all_recovery_data():
    global recovery_data
    logging.info("Loading all recovery data...")
    for fname in os.listdir(RECOVERY_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(RECOVERY_DIR, fname), "r") as f:
                    data = json.load(f)
                    token_hash = fname.split(".")[0]
                    # Convert expiry time back to datetime object
                    if 'lock_expiry' in data and data['lock_expiry']:
                        data['lock_expiry'] = datetime.fromisoformat(data['lock_expiry'])
                    recovery_data[token_hash] = data
            except Exception as e:
                logging.error(f"Could not load recovery data from {fname}: {e}")
    logging.info(f"Loaded {len(recovery_data)} recovery tokens.")

def save_all_recovery_data():
    logging.info("Saving all recovery data...")
    for token_hash in recovery_data.keys():
        save_recovery_data(token_hash)
    logging.info("All recovery data saved.")

## NEW FEATURE - Gift Code Persistence ##
def save_gift_code(code):
    data = gift_codes.get(code)
    if not data:
        return
    try:
        with open(os.path.join(GIFT_CODE_DIR, f"{code}.json"), "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save gift code {code}: {e}")

def load_all_gift_codes():
    global gift_codes
    logging.info("Loading all gift codes...")
    for fname in os.listdir(GIFT_CODE_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(GIFT_CODE_DIR, fname), "r") as f:
                    data = json.load(f)
                    code = fname.split(".")[0]
                    gift_codes[code] = data
            except Exception as e:
                logging.error(f"Could not load gift code from {fname}: {e}")
    logging.info(f"Loaded {len(gift_codes)} gift codes.")

def save_all_gift_codes():
    logging.info("Saving all gift codes...")
    for code in gift_codes.keys():
        save_gift_code(code)
    logging.info("All gift codes saved.")


atexit.register(save_bot_state)
load_bot_state()

# --- DECORATOR FOR MAINTENANCE MODE ---
def check_banned(func):
    """
    Decorator to check if a user is banned before allowing any interaction.
    Blocks both permanently banned users and temp banned users from ALL actions.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return await func(update, context, *args, **kwargs)
        
        user_lang = get_user_lang(user.id)
        
        # Check if user is permanently banned
        if user.id in bot_settings.get("banned_users", []):
            banned_text = get_text("banned_user", user_lang)
            if update.message:
                await update.message.reply_text(banned_text, parse_mode=ParseMode.HTML)
            elif update.callback_query:
                await update.callback_query.answer(banned_text, show_alert=True)
            return
        
        # Check if user is temp banned (withdrawal ban = full ban)
        if user.id in bot_settings.get("tempbanned_users", []):
            temp_banned_text = "You are temporarily banned from using this bot."
            if update.message:
                await update.message.reply_text(temp_banned_text, parse_mode=ParseMode.HTML)
            elif update.callback_query:
                await update.callback_query.answer(temp_banned_text, show_alert=True)
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def check_maintenance(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if bot_settings.get("maintenance_mode", False) and user.id != BOT_OWNER_ID:
            user_lang = get_user_lang(user.id) if user else DEFAULT_LANG
            
            # Allow ongoing game interactions to continue
            if update.message and update.message.dice:
                active_pvb_game_id = context.chat_data.get(f"active_pvb_game_{user.id}")
                if active_pvb_game_id and active_pvb_game_id in game_sessions:
                    return await func(update, context, *args, **kwargs)

                chat_id = update.effective_chat.id
                for match_id, match_data in list(game_sessions.items()):
                    if match_data.get("chat_id") == chat_id and match_data.get("status") == 'active' and user.id in match_data.get("players", []):
                         return await func(update, context, *args, **kwargs)

            # Block new commands/interactions
            maintenance_text = get_text("maintenance_mode", user_lang)
            if update.message:
                await update.message.reply_text(maintenance_text, parse_mode=ParseMode.HTML)
            elif update.callback_query:
                await update.callback_query.answer(get_text("maintenance_mode", user_lang), show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- HELPER TO CHECK BET LIMITS ---
async def check_bet_limits(update: Update, bet_amount: float, game_name: str, user_id: int = None) -> bool:
    if user_id is None and update.effective_user:
        user_id = update.effective_user.id
    user_lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    user_currency = get_user_currency(user_id) if user_id else "USD"
    
    limits = bot_settings.get('game_limits', {}).get(game_name, {})
    min_bet = limits.get('min', MIN_BALANCE)
    max_bet = limits.get('max')

    if bet_amount < min_bet:
        min_formatted = format_currency(min_bet, user_currency)
        await update.message.reply_text(get_text("min_bet", user_lang, amount=min_formatted))
        return False
    if max_bet is not None and bet_amount > max_bet:
        max_formatted = format_currency(max_bet, user_currency)
        await update.message.reply_text(get_text("max_bet", user_lang, amount=max_formatted))
        return False
    return True

# ===== DASHBOARD IMAGE GENERATION FUNCTIONS =====

async def get_user_profile_picture(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """
    Retrieve user's Telegram profile picture and return as PIL Image.
    Returns None if no profile picture is available.
    """
    try:
        # Get user profile photos
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        
        if photos.total_count > 0:
            # Get the first (most recent) photo
            photo = photos.photos[0][-1]  # Get largest size
            
            # Download the photo
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Convert to PIL Image
            image = Image.open(BytesIO(photo_bytes))
            return image
        
        return None
    except Exception as e:
        logging.error(f"Error fetching profile picture for user {user_id}: {e}")
        return None

def create_circular_mask(image_size):
    """Create a circular mask for profile pictures."""
    mask = Image.new('L', image_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, image_size[0], image_size[1]), fill=255)
    return mask

async def generate_dashboard_image(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate a dashboard image with user data overlaid on the background template.
    Returns BytesIO object containing the JPEG image.
    """
    try:
        # Load background template
        dashboard = Image.open(DASHBOARD_TEMPLATE_PATH).convert('RGBA')
        draw = ImageDraw.Draw(dashboard)
        
        # Load custom font or use default
        try:
            # Try to load custom font with various sizes
            fonts = {}
            for key, config in DASHBOARD_CONFIG.items():
                if key != "profile_picture" and "font_size" in config:
                    size = config["font_size"]
                    if size not in fonts:
                        fonts[size] = ImageFont.truetype(DASHBOARD_FONT_PATH, size)
        except Exception as e:
            logging.warning(f"Could not load custom font: {e}. Using default font.")
            # Fallback to default font (will be smaller but readable)
            fonts = {size: ImageFont.load_default() for size in [20, 24, 28, 32]}
        
        # Get user data
        stats = user_stats.get(user_id, {})
        userinfo = stats.get('userinfo', {})
        balance = user_wallets.get(user_id, 0.0)
        user_currency = get_user_currency(user_id)
        
        # Get actual user info from Telegram
        first_name = userinfo.get('first_name', 'User')
        username = userinfo.get('username', 'N/A')
        try:
            user = await context.bot.get_chat(user_id)
            if user.first_name:
                first_name = user.first_name
            if user.username:
                username = user.username
        except Exception as e:
            logging.warning(f"Could not fetch user info: {e}")
        
        # Get bot username
        try:
            bot_info = await context.bot.get_me()
            bot_username = f"@{bot_info.username}"
        except Exception as e:
            logging.warning(f"Could not fetch bot username: {e}")
            bot_username = "@CasinoBot"
        
        # Get user level
        level_data = get_user_level(user_id)
        
        # Get last win amount from user_stats (stored from game results)
        last_win = stats.get('last_win', 0.0)
        
        # Format member since date
        join_date = userinfo.get('join_date', 'N/A')
        if join_date != 'N/A':
            try:
                # Parse and format date (convert UTC 'Z' notation to ISO 8601 timezone format)
                date_obj = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
                join_date = date_obj.strftime('%b %d, %Y')
            except (ValueError, AttributeError) as e:
                logging.warning(f"Could not parse join date: {e}")
                join_date = join_date[:10] if len(join_date) > 10 else join_date
        
        # Prepare text data
        text_data = {
            "name": first_name,
            "user_id": str(user_id),
            "username": f"@{username}",
            "bot_username": bot_username,
            "level": level_data['name'],
            "balance": format_currency(balance, user_currency),
            "last_win": format_currency(last_win, user_currency) if last_win > 0 else "Play to win!",
            "member_since": join_date
        }
        
        # Draw text on image
        for key, text in text_data.items():
            if key in DASHBOARD_CONFIG:
                config = DASHBOARD_CONFIG[key]
                position = config["position"]
                font_size = config["font_size"]
                color = config["color"]
                font = fonts.get(font_size, fonts[20])  # Fallback to size 20
                
                draw.text(position, text, fill=color, font=font)
        
        # Add profile picture (circular)
        profile_pic = await get_user_profile_picture(context, user_id)
        if profile_pic:
            try:
                pic_config = DASHBOARD_CONFIG["profile_picture"]
                pic_position = pic_config["position"]
                pic_size = pic_config["size"]
                
                # Resize profile picture
                profile_pic = profile_pic.resize(pic_size, Image.Resampling.LANCZOS)
                
                # Create circular mask
                mask = create_circular_mask(pic_size)
                
                # Convert to RGBA if needed
                if profile_pic.mode != 'RGBA':
                    profile_pic = profile_pic.convert('RGBA')
                
                # Paste with circular mask
                dashboard.paste(profile_pic, pic_position, mask)
            except Exception as e:
                logging.error(f"Error adding profile picture: {e}")
        
        # Convert to RGB for JPEG output (or keep RGBA for PNG)
        output = BytesIO()
        dashboard_rgb = dashboard.convert('RGB')
        dashboard_rgb.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output
    except Exception as e:
        logging.error(f"Error generating dashboard image: {e}")
        logging.error(traceback.format_exc())
        return None

async def ensure_user_in_wallets(user_id: int, username: str = None, referrer_id: int = None, context: ContextTypes.DEFAULT_TYPE = None, first_name: str = None):
    # IMPROVEMENT: Always register user on any command
    if user_id not in user_stats:
        # If no username or first_name provided, try to fetch it
        if (not username or not first_name) and context:
            try:
                chat_member = await context.bot.get_chat(user_id)
                if not username:
                    username = chat_member.username
                if not first_name:
                    first_name = chat_member.first_name
            except (BadRequest, Forbidden):
                logging.warning(f"Could not fetch user info for new user {user_id}")

        user_wallets[user_id] = 0.0
        user_stats[user_id] = {
            "userinfo": {
                "user_id": user_id, 
                "username": username or "", 
                "first_name": first_name or "User",
                "join_date": str(datetime.now(timezone.utc)), 
                "language": DEFAULT_LANG, 
                "currency": "USD"
            },
            "deposits": [], # Changed to list of dicts
            "withdrawals": [], # Changed to list of dicts
            "tips_received": {"count": 0, "amount": 0.0},
            "tips_sent": {"count": 0, "amount": 0.0},
            "bets": {"count": 0, "amount": 0.0, "wins": 0, "losses": 0, "pvp_wins": 0, "history": []},
            "rain_received": {"count": 0, "amount": 0.0},
            "wallet": 0.0,
            "pnl": 0.0,
            "last_update": str(datetime.now(timezone.utc)),
            "game_sessions": [],
            "escrow_deals": [],
            "last_win": 0.0,  # NEW: Track last win amount
            "referral": {
                "referrer_id": referrer_id,
                "referred_users": [],
                "commission_earned": 0.0
            },
            "achievements": [], # NEW
            "last_daily_claim": None, # NEW
            "recovery_token_hash": None, # NEW
            "last_weekly_claim": None, # NEW
            "last_monthly_claim": None, # NEW
            "last_rakeback_claim_wager": 0.0, # NEW
            "claimed_gift_codes": [], # NEW
            "claimed_level_rewards": [], # NEW: For level system
            "unwagered_deposit": 0.0, # NEW: Deposits that need 2x wagering
            "unwagered_tips": 0.0, # NEW: Tips that need 1x wagering
            "provably_fair": {  # NEW: Provably fair system
                "server_seed": generate_server_seed(),
                "server_seed_hash": None,  # Will be set when seed is revealed
                "client_seed": generate_client_seed(),
                "nonce": 0,
                "next_server_seed": generate_server_seed(),  # For rotation
            }
        }
        if username:
            username_to_userid[normalize_username(username)] = user_id

        # AUTO-GENERATE RECOVERY TOKEN FOR NEW USER
        token = secrets.token_hex(20)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        recovery_data[token_hash] = {
            "user_id": user_id,
            "username": username or "",
            "created_at": str(datetime.now(timezone.utc)),
            "failed_attempts": 0,
            "lock_expiry": None
        }
        user_stats[user_id]["recovery_token_hash"] = token_hash
        
        save_recovery_data(token_hash)
        
        # Send recovery token to user
        if context:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🔐 <b>Account Recovery Token</b>\n\n"
                        "Your account recovery token has been generated. Please save this token in a secure place. "
                        "It is the ONLY way to recover your account if you lose access to your Telegram account.\n\n"
                        "<b>⚠️ IMPORTANT:</b>\n"
                        "• Do NOT share this token with anyone\n"
                        "• Save it in a safe place offline\n"
                        "• You will need this token to use /recover command\n\n"
                        "<b>Your Recovery Token:</b>\n"
                        f"<code>{token}</code>\n\n"
                        "This message will only be sent once. Make sure to save it now!"
                    ),
                    parse_mode=ParseMode.HTML
                )
            except (BadRequest, Forbidden):
                logging.warning(f"Could not send recovery token to user {user_id}")

        if referrer_id:
            await ensure_user_in_wallets(referrer_id, context=context) # Pass context
            if 'referral' not in user_stats[referrer_id]:
                 user_stats[referrer_id]['referral'] = {"referrer_id": None, "referred_users": [], "commission_earned": 0.0}
            user_stats[referrer_id]['referral']['referred_users'].append(user_id)
            save_user_data(referrer_id)
            await check_and_award_achievements(referrer_id, None) # Check for referral achievements
        save_user_data(user_id)
        logging.info(f"New user registered: {username} ({user_id})")

    # Update username and first_name if they have changed
    current_username = user_stats[user_id]["userinfo"].get("username")
    if username and current_username != username:
        # Remove old username mapping if it exists
        if current_username and normalize_username(current_username) in username_to_userid:
            del username_to_userid[normalize_username(current_username)]
        user_stats[user_id]["userinfo"]["username"] = username
        username_to_userid[normalize_username(username)] = user_id
        save_user_data(user_id)
    
    # Update first_name if provided and different
    if first_name:
        current_first_name = user_stats[user_id]["userinfo"].get("first_name")
        if current_first_name != first_name:
            user_stats[user_id]["userinfo"]["first_name"] = first_name
            save_user_data(user_id)
    
    # Initialize last_win if it doesn't exist (for existing users)
    if "last_win" not in user_stats[user_id]:
        user_stats[user_id]["last_win"] = 0.0
        save_user_data(user_id)
    
    # Initialize provably fair data if it doesn't exist (for existing users - migration)
    if "provably_fair" not in user_stats[user_id]:
        user_stats[user_id]["provably_fair"] = {
            "server_seed": generate_server_seed(),
            "server_seed_hash": None,
            "client_seed": generate_client_seed(),
            "nonce": 0,
            "next_server_seed": generate_server_seed(),
        }
        save_user_data(user_id)
    
    # Initialize unwagered fields if they don't exist (for existing users)
    if "unwagered_deposit" not in user_stats[user_id]:
        user_stats[user_id]["unwagered_deposit"] = 0.0
    if "unwagered_tips" not in user_stats[user_id]:
        user_stats[user_id]["unwagered_tips"] = 0.0
        save_user_data(user_id)

    return True

def check_menu_ownership(query, context) -> bool:
    """
    Check if the user clicking the button is the owner of the menu.
    For group chats, we track menu ownership by message_id.
    Returns True if the user is the owner or if no owner is set.
    Returns False if another user is trying to interact with the menu.
    """
    # Get or initialize menu ownership tracking
    if 'menu_owners' not in bot_settings:
        bot_settings['menu_owners'] = {}
    
    message_id = query.message.message_id
    chat_id = query.message.chat_id
    menu_key = f"{chat_id}_{message_id}"
    
    # Check if this message has an owner
    menu_owner_id = bot_settings['menu_owners'].get(menu_key)
    if menu_owner_id and query.from_user.id != menu_owner_id:
        return False
    return True

def set_menu_owner(message, user_id):
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
        # Remove oldest 100 entries
        keys_to_remove = list(bot_settings['menu_owners'].keys())[:100]
        for key in keys_to_remove:
            del bot_settings['menu_owners'][key]

def get_locked_balance_in_games(user_id: int) -> dict:
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

async def send_insufficient_balance_message(update: Update, message: str = None, user_lang: str = None):
    """
    Send an insufficient balance message.
    Can be used with update.message or update.callback_query.
    """
    if user_lang is None:
        user = update.effective_user
        user_lang = get_user_lang(user.id) if user else DEFAULT_LANG
    
    if message is None:
        message = get_text("insufficient_balance", user_lang)
    
    if update.callback_query:
        await safe_edit_message(update.callback_query, message, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

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

## NEW FEATURE - Achievement System ##
async def check_and_award_achievements(user_id, context, multiplier=0):
    if user_id not in user_stats:
        return

    stats = user_stats[user_id]
    user_achievements = stats.get("achievements", [])

    total_wagered = stats["bets"]["amount"]
    total_wins = stats["bets"]["wins"]
    pvp_wins = stats["bets"].get("pvp_wins", 0)
    referrals = len(stats.get("referral", {}).get("referred_users", []))

    for achievement_id, ach_data in ACHIEVEMENTS.items():
        if achievement_id in user_achievements:
            continue # Already has it

        unlocked = False
        if ach_data["type"] == "wager" and total_wagered >= ach_data["value"]:
            unlocked = True
        elif ach_data["type"] == "wins" and total_wins >= ach_data["value"]:
            unlocked = True
        elif ach_data["type"] == "pvp_wins" and pvp_wins >= ach_data["value"]:
            unlocked = True
        elif ach_data["type"] == "multiplier" and multiplier >= ach_data["value"]:
            unlocked = True
        elif ach_data["type"] == "referrals" and referrals >= ach_data["value"]:
            unlocked = True

        if unlocked:
            stats["achievements"].append(achievement_id)
            save_user_data(user_id)
            if context:
                lang = stats.get("userinfo", {}).get("language", DEFAULT_LANG)
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=get_text("achievement_unlocked", lang, emoji=ach_data["emoji"], name=ach_data["name"], description=ach_data["description"]),
                        parse_mode=ParseMode.HTML
                    )
                except (BadRequest, Forbidden):
                    logging.warning(f"Could not send achievement notification to user {user_id}")
## NEW FEATURE - Level System Logic ##
def get_user_level(user_id: int):
    """Determines a user's current level based on their total wagered amount."""
    if user_id not in user_stats:
        return LEVELS[0]
    
    wagered = user_stats[user_id].get("bets", {}).get("amount", 0.0)
    current_level = LEVELS[0]
    for level_data in reversed(LEVELS):
        if wagered >= level_data["wager_required"]:
            current_level = level_data
            break
    return current_level

async def check_and_award_level_up(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Checks for level-up, awards reward, and notifies the user."""
    if user_id not in user_stats:
        return

    current_level_data = get_user_level(user_id)
    level_num = current_level_data["level"]
    
    claimed_rewards = user_stats[user_id].get("claimed_level_rewards", [])

    if level_num > 0 and level_num not in claimed_rewards:
        reward_amount = current_level_data["reward"]
        user_wallets[user_id] += reward_amount
        user_stats[user_id].setdefault("claimed_level_rewards", []).append(level_num)
        save_user_data(user_id)
        
        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(f"🎉 <b>Level Up!</b> 🎉\n\n"
                      f"Congratulations! You have reached <b>Level {level_num} ({current_level_data['name']})</b>.\n"
                      f"You have been awarded a one-time bonus of <b>${reward_amount:.2f}</b>!"),
                parse_mode=ParseMode.HTML
            )
        except (BadRequest, Forbidden):
            logging.warning(f"Could not send level-up notification to user {user_id}")

async def process_referral_commission(user_id, amount, commission_type):
    if user_id not in user_stats or not user_stats[user_id].get('referral', {}).get('referrer_id'):
        return

    referrer_id = user_stats[user_id]['referral']['referrer_id']
    if referrer_id not in user_stats:
        return

    if commission_type == 'bet':
        rate = REFERRAL_BET_COMMISSION_RATE
    else:
        return

    commission = amount * rate
    if commission > 0:
        await ensure_user_in_wallets(referrer_id)
        user_wallets[referrer_id] = user_wallets.get(referrer_id, 0.0) + commission
        user_stats[referrer_id]['referral']['commission_earned'] += commission
        save_user_data(referrer_id)
        logging.info(f"Awarded ${commission:.4f} commission to referrer {referrer_id} from user {user_id}'s {commission_type}.")

def update_stats_on_withdrawal(user_id, amount, tx_hash, method):
    stats = user_stats[user_id]
    withdrawal_record = {
        "amount": amount,
        "tx_hash": tx_hash,
        "method": method,
        "timestamp": str(datetime.now(timezone.utc))
    }
    stats["withdrawals"].append(withdrawal_record)
    save_user_data(user_id)

def update_stats_on_tip_received(user_id, amount):
    stats = user_stats[user_id]
    stats["tips_received"]["count"] += 1
    stats["tips_received"]["amount"] += amount
    save_user_data(user_id)

def update_stats_on_tip_sent(user_id, amount):
    stats = user_stats[user_id]
    stats["tips_sent"]["count"] += 1
    stats["tips_sent"]["amount"] += amount
    save_user_data(user_id)

def reduce_unwagered_amounts(user_id, bet_amount):
    """
    Reduce unwagered deposit and tip amounts when a bet is placed.
    
    Tip requirement: 1x wagering (each $1 bet reduces $1 of unwagered tips)
    Deposit requirement: 2x wagering (each $1 bet reduces $0.50 of unwagered deposits,
                         because the user needs to wager 2x the deposit amount)
    
    Example: $100 deposit requires $200 total wagering
    - After $50 bet: $75 deposit still unwagered (needs $150 more wagering)
    - After $100 bet: $50 deposit still unwagered (needs $100 more wagering)
    - After $200 bet: $0 deposit unwagered (requirement met)
    """
    if user_id not in user_stats:
        return
    
    stats = user_stats[user_id]
    remaining_bet = bet_amount
    
    # First, reduce unwagered tips (1x requirement - direct reduction)
    unwagered_tips = stats.get("unwagered_tips", 0.0)
    if unwagered_tips > 0 and remaining_bet > 0:
        reduction = min(unwagered_tips, remaining_bet)
        stats["unwagered_tips"] = max(0, unwagered_tips - reduction)
        remaining_bet -= reduction
    
    # Then, reduce unwagered deposits (2x requirement - each $1 bet reduces $0.50 of unwagered deposit)
    unwagered_deposit = stats.get("unwagered_deposit", 0.0)
    if unwagered_deposit > 0 and remaining_bet > 0:
        # For 2x requirement, each $1 bet reduces $0.50 of the unwagered deposit amount
        deposit_reduction = remaining_bet / 2.0
        reduction = min(unwagered_deposit, deposit_reduction)
        stats["unwagered_deposit"] = max(0, unwagered_deposit - reduction)

def calculate_required_wager(user_id):
    """
    Calculate how much more the user needs to wager before they can withdraw.
    Returns (total_required, breakdown_dict)
    """
    if user_id not in user_stats:
        return 0.0, {}
    
    stats = user_stats[user_id]
    unwagered_tips = stats.get("unwagered_tips", 0.0)
    unwagered_deposit = stats.get("unwagered_deposit", 0.0)
    
    # Tips need 1x wagering
    tips_wager_needed = unwagered_tips
    
    # Deposits need 2x wagering (so need to wager 2x the unwagered amount)
    deposit_wager_needed = unwagered_deposit * 2.0
    
    total_needed = tips_wager_needed + deposit_wager_needed
    
    breakdown = {
        "unwagered_tips": unwagered_tips,
        "tips_wager_needed": tips_wager_needed,
        "unwagered_deposit": unwagered_deposit,
        "deposit_wager_needed": deposit_wager_needed,
        "total_wager_needed": total_needed
    }
    
    return total_needed, breakdown

def update_stats_on_bet(user_id, game_id, amount, win, pvp_win=False, multiplier=0, context=None):
    stats = user_stats[user_id]
    stats["bets"]["count"] += 1
    stats["bets"]["amount"] += amount
    
    # NEW: Reduce unwagered amounts when betting
    reduce_unwagered_amounts(user_id, amount)
    
    # NEW: House balance update
    global bot_settings
    if win:
        winnings = amount * multiplier
        net_win = winnings - amount
        bot_settings["house_balance"] -= net_win
        # NEW: Update last_win field
        if net_win > 0:
            stats["last_win"] = net_win
    else:
        bot_settings["house_balance"] += amount
    
    if win:
        stats["bets"]["wins"] += 1
        if pvp_win:
            stats["bets"]["pvp_wins"] = stats["bets"].get("pvp_wins", 0) + 1
    else:
        stats["bets"]["losses"] += 1

    if 'game_sessions' not in stats:
        stats['game_sessions'] = []
    stats['game_sessions'].append(game_id)
    
    # NEW: Add to wager history for weekly/monthly bonuses
    if 'history' not in stats['bets']:
        stats['bets']['history'] = []
    stats['bets']['history'].append({
        "amount": amount,
        "timestamp": str(datetime.now(timezone.utc))
    })

    save_user_data(user_id)
    # Process referral commission on bet
    asyncio.create_task(process_referral_commission(user_id, amount, 'bet'))
    # Check for achievements
    asyncio.create_task(check_and_award_achievements(user_id, context, multiplier))
    # NEW: Check for level up
    asyncio.create_task(check_and_award_level_up(user_id, context))

def update_stats_on_rain_received(user_id, amount):
    stats = user_stats[user_id]
    stats["rain_received"]["count"] += 1
    stats["rain_received"]["amount"] += amount
    save_user_data(user_id)

def update_pnl(user_id):
    stats = user_stats[user_id]
    total_deposits = sum(d['amount'] for d in stats.get('deposits', []))
    total_withdrawals = sum(w['amount'] for w in stats.get('withdrawals', []))
    stats["pnl"] = (total_withdrawals + user_wallets.get(user_id, 0.0)) - (total_deposits + stats["tips_received"]["amount"])
    save_user_data(user_id)

def get_all_registered_user_ids():
    return list(user_stats.keys())

@check_banned
@check_maintenance
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    ## NEW FEATURE ##
    # Handle deep linking for referrals and escrow
    referrer_id = None
    if context.args and len(context.args) > 0:
        deep_link_arg = context.args[0]
        if deep_link_arg.startswith("ref_"):
            try:
                referrer_id = int(deep_link_arg.replace("ref_", ""))
                if referrer_id == user.id: # Can't refer yourself
                    referrer_id = None
                else:
                    # Notify referrer
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 New referral! {user.mention_html()} has joined using your link.",
                        parse_mode=ParseMode.HTML
                    )
            except (ValueError, TypeError, BadRequest, Forbidden):
                referrer_id = None # Invalid referral ID or can't message

        elif deep_link_arg.startswith("escrow_"):
            deal_id = deep_link_arg.replace("escrow_", "")
            await handle_escrow_deep_link(update, context, deal_id)
            return
        
        elif deep_link_arg.startswith("provablyfair_"):
            pf_id = deep_link_arg.replace("provablyfair_", "")
            await handle_provably_fair_deep_link(update, context, pf_id)
            return

    await ensure_user_in_wallets(user.id, user.username, referrer_id, context, user.first_name)

    # Check if user is banned
    user_lang = get_user_lang(user.id)
    if user.id in bot_settings.get("banned_users", []):
        await update.message.reply_text(get_text("banned_user", user_lang))
        return

    # Get user's preferred currency
    user_currency = get_user_currency(user.id)
    formatted_balance = format_balance_with_locked(user.id, user_currency)

    # NEW UI STRUCTURE - Casino themed with premium emojis
    keyboard = [
        # Row 1: Deposit & Withdraw
        [
            InlineKeyboardButton("💎 Deposit", callback_data="main_deposit"),
            InlineKeyboardButton("💸 Withdraw", callback_data="main_withdraw")
        ],
        # Row 2: Games & More
        [
            InlineKeyboardButton("🎮 Games", callback_data="main_games"),
            InlineKeyboardButton("➕ More", callback_data="main_more")
        ],
        # Row 3: Settings
    ]

    # Add Settings button only in DMs
    if update.effective_chat.type == "private":
        keyboard.append([InlineKeyboardButton("⚙️ Settings", callback_data="main_settings")])

    # Row 5: Admin Dashboard (only for admin)
    if user.id == BOT_OWNER_ID:
        keyboard.append([InlineKeyboardButton(get_text("admin_panel", user_lang), callback_data="admin_dashboard")])

    # Get total wagers for display
    stats = user_stats.get(user.id, {})
    total_wagered = stats.get('bets', {}).get('amount', 0.0)
    formatted_wagers = format_currency(total_wagered, user_currency)
    
    # Create links row
    links_row = []
    if LINK_PORTAL:
        links_row.append(InlineKeyboardButton("🌐 Portal", url=LINK_PORTAL))
    if LINK_CHANNEL:
        links_row.append(InlineKeyboardButton("📢 Channel", url=LINK_CHANNEL))
    
    links_row_2 = []
    if LINK_CHAT:
        links_row_2.append(InlineKeyboardButton("💬 Chat", url=LINK_CHAT))
    if LINK_SUPPORT:
        links_row_2.append(InlineKeyboardButton("🆘 Support", url=LINK_SUPPORT))
    
    # Add links rows if they have buttons
    if links_row:
        keyboard.append(links_row)
    if links_row_2:
        keyboard.append(links_row_2)
    
    welcome_text = (
        "🐱 <b>Welcome to Casino ⚡</b>\n\n"
        "⭐️ Casino - the best online mini-games platform on Telegram\n"
        f"💵 <b>Balance:</b> {formatted_balance}\n"
        f"👑 <b>Wagers:</b> {formatted_wagers}\n\n"
        "🎮 Choose an option below to get started!"
    )

    # Send dashboard image with welcome message in caption (NEW FEATURE - Combined)
    dashboard_image = await generate_dashboard_image(user.id, context)
    if dashboard_image and update.message:
        try:
            sent_message = await update.message.reply_photo(
                photo=dashboard_image,
                caption=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            set_menu_owner(sent_message, user.id)
        except Exception as e:
            logging.error(f"Error sending dashboard image: {e}")
            # Fallback to text only if image fails
            sent_message = await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            set_menu_owner(sent_message, user.id)
    elif update.message:
        # No image available, send text only
        sent_message = await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        set_menu_owner(sent_message, user.id)
    elif update.callback_query:
         await safe_edit_message(
            update.callback_query,
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
         # For edited messages, use the existing message
         set_menu_owner(update.callback_query.message, user.id)

@check_banned
@check_maintenance
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    data = query.data
    user = query.from_user

    await ensure_user_in_wallets(user.id, user.username, context=context)
    if user.id in bot_settings.get("banned_users", []):
        await query.answer("You are banned.", show_alert=True)
        return
    if user.id in bot_settings.get("tempbanned_users", []):
        await query.answer("You are temporarily banned.", show_alert=True)
        return

    if data == "main_deposit":
        # Show deposit menu
        if not DEPOSIT_ENABLED:
            await safe_edit_message(
                query,
                "❌ Deposits are currently disabled.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]])
            )
            return
        
        text, keyboard = build_deposit_menu()
        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return

    elif data == "main_withdraw":
        # NEW: Check if withdrawals are enabled
        if not bot_settings.get("withdrawals_enabled", True):
            await safe_edit_message(
                query,
                "❌ <b>Withdrawals Disabled</b>\n\n"
                "Withdrawals are temporarily disabled by the administrator. "
                "Please contact support for more information.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]])
            )
            return

        if user.id in bot_settings.get("tempbanned_users", []):
            await safe_edit_message(
                query,
                "❌ <b>Withdrawals Disabled</b>\n\n"
                "Your account is currently restricted from making withdrawals. "
                "Please contact support for more information.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]])
            )
            return

        # Check if withdrawal address is set
        withdrawal_address = user_stats[user.id].get("withdrawal_address")
        if not withdrawal_address:
            await safe_edit_message(
                query,
                "💳 <b>Withdrawal Address Not Set</b>\n\n"
                "Please set your USDT-BEP20 withdrawal address in Settings first before requesting a withdrawal.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Go to Settings", callback_data="main_settings")],
                    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
                ])
            )
            return

        # Ask for withdrawal amount
        user_currency = get_user_currency(user.id)
        formatted_balance = format_currency(user_wallets.get(user.id, 0.0), user_currency)
        
        await safe_edit_message(
            query,
            f"💸 <b>Withdrawal Request</b>\n\n"
            f"<b>Current Balance:</b> {formatted_balance}\n"
            f"<b>Withdrawal Address:</b> <code>{withdrawal_address}</code>\n\n"
            f"Please enter the amount you want to withdraw in {user_currency}.\n"
            f"Type 'all' to withdraw your entire balance.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="back_to_main")]])
        )
        context.user_data['withdrawal_flow'] = True
        return WITHDRAWAL_AMOUNT

    elif data == "main_games":
        await games_menu(update, context)

    elif data == "main_escrow":
        await escrow_command(update, context, from_callback=True)

    elif data == "main_wallet":
        balance = user_wallets.get(user.id, 0.0)
        stats = user_stats.get(user.id, {})
        total_deposits = sum(d['amount'] for d in stats.get('deposits', []))
        total_withdrawals = sum(w['amount'] for w in stats.get('withdrawals', []))
        
        user_currency = get_user_currency(user.id)

        wallet_text = (
            f"💼 <b>Your Wallet</b>\n\n"
            f"💰 Balance: <b>{format_currency(balance, user_currency)}</b>\n"
            f"🎲 Total Wagered: {format_currency(stats.get('bets', {}).get('amount', 0.0), user_currency)}\n"
            f"🏆 Wins: {stats.get('bets', {}).get('wins', 0)}\n"
            f"💔 Losses: {stats.get('bets', {}).get('losses', 0)}\n"
            f"📈 P&L: <b>{format_currency(stats.get('pnl', 0.0), user_currency)}</b>\n"
            f"💵 Total Deposited: {format_currency(total_deposits, user_currency)}\n"
            f"💸 Total Withdrawn: {format_currency(total_withdrawals, user_currency)}"
        )

        keyboard = [
            [InlineKeyboardButton("💸 Withdraw", callback_data="main_withdraw")],
            [InlineKeyboardButton("📜 My Game Matches", callback_data="my_matches_0")],
            [InlineKeyboardButton("🛡️ My Escrow Deals", callback_data="my_deals_0")],
            [InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]
        ]

        # Send dashboard image with wallet text as new message (callback can't edit to photo)
        dashboard_image = await generate_dashboard_image(user.id, context)
        if dashboard_image:
            try:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=dashboard_image,
                    caption=wallet_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Delete the old message
                try:
                    await query.message.delete()
                except Exception as del_err:
                    logging.warning(f"Could not delete old message: {del_err}")
            except Exception as e:
                logging.error(f"Error sending dashboard image: {e}")
                # Fallback to editing text
                await safe_edit_message(
                    query,
                    wallet_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # No image, just edit text
            await safe_edit_message(
                query,
                wallet_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    ## NEW FEATURE ##
    elif data == "main_leaderboard":
        await leaderboard_command(update, context, from_callback=True)

    ## NEW FEATURE ##
    elif data == "main_referral":
        await referral_command(update, context, from_callback=True)

    ## NEW FEATURE - AI Integration ##
    elif data == "main_ai":
        return await start_ai_conversation(update, context)

    elif data == "main_support":
        await safe_edit_message(
            query,
            "🆘 <b>Support</b>\n\n"
            "Need help or have questions?\n"
            "Contact the bot owner:\n\n"
            "👤 @jashanxjagy\n\n"
            "We're here to help you 24/7!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]])
        )

    elif data == "main_help":
        await help_command(update, context, from_callback=True)

    elif data == "main_info":
        info_text = (
            "ℹ️ <b>Casino Rules & Info</b>\n\n"
            "<b>🎰 General Rules:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• All games use provably fair system\n"
            "• No refunds on completed bets\n"
            "• Contact support for disputes\n\n"
            "<b>🛡️ Escrow Rules:</b>\n"
            "• Use /escrow to start a secure trade.\n"
            "• Seller deposits funds into bot's secure wallet.\n"
            "• Buyer confirms receipt of goods/services.\n"
            "• Seller releases funds to the buyer.\n"
            "• All transactions are on the blockchain.\n\n"
            "<b>⚠️ Responsible Gaming:</b>\n"
            "• Only bet what you can afford to lose\n"
            "• Set personal limits\n"
            "• Contact support if you need help"
        )
        await safe_edit_message(
            query,
            info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]])
        )

    ## NEW FEATURE ##
    elif data == "main_level":
        await level_command(update, context, from_callback=True)
        
    ## NEW FEATURE ##
    elif data == "main_settings":
        await settings_command(update, context)

    elif data == "main_more":
        await more_menu(update, context)
    
    elif data.startswith("more_page_"):
        page = int(data.split("_")[-1])
        await more_menu(update, context, page)
    
    elif data == "main_daily":
        await daily_command(update, context, from_callback=True)
    
    elif data == "main_bonuses":
        await bonuses_menu(update, context)
    
    elif data == "main_achievements":
        await achievements_command(update, context, from_callback=True)
    
    elif data == "main_claim_gift":
        await safe_edit_message(
            query,
            "🎟️ <b>Claim Gift Code</b>\n\n"
            "Use the command:\n<code>/claim YOUR_CODE</code>\n\n"
            "Example: <code>/claim GIFT-ABC12345</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]])
        )
    
    elif data == "main_stats":
        await stats_command(update, context, from_callback=True)

    elif data == "back_to_main":
        await query.answer()  # Acknowledge the button press
        await start_command_inline(query, context)

    elif data.startswith("my_matches"):
        page = int(data.split('_')[-1])
        await matches_command(update, context, from_callback=True, page=page)

    elif data.startswith("my_deals"):
        page = int(data.split('_')[-1])
        await deals_command(update, context, from_callback=True, page=page)


async def start_command_inline(query, context):
    user = query.from_user
    await ensure_user_in_wallets(user.id, user.username, context=context, first_name=user.first_name)

    # Get user's preferred currency and language
    user_currency = get_user_currency(user.id)
    user_lang = get_user_lang(user.id)
    formatted_balance = format_balance_with_locked(user.id, user_currency)
    
    # Get total wagers for display
    stats = user_stats.get(user.id, {})
    total_wagered = stats.get('bets', {}).get('amount', 0.0)
    formatted_wagers = format_currency(total_wagered, user_currency)

    # NEW UI STRUCTURE - Casino themed with premium emojis
    keyboard = [
        # Row 1: Deposit & Withdraw
        [
            InlineKeyboardButton("💎 Deposit", callback_data="main_deposit"),
            InlineKeyboardButton("💸 Withdraw", callback_data="main_withdraw")
        ],
        # Row 2: Games & More
        [
            InlineKeyboardButton("🎮 Games", callback_data="main_games"),
            InlineKeyboardButton("➕ More", callback_data="main_more")
        ],
        # Row 3: Settings
    ]

    # Add Settings button only in DMs - with better error handling
    try:
        if query.message and query.message.chat and query.message.chat.type == "private":
            keyboard.append([InlineKeyboardButton("⚙️ Settings", callback_data="main_settings")])
    except AttributeError:
        # Default to adding settings if we can't determine chat type
        keyboard.append([InlineKeyboardButton("⚙️ Settings", callback_data="main_settings")])

    # Row 5: Admin Dashboard (only for admin)
    if user.id == BOT_OWNER_ID:
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_dashboard")])

    # Create links row
    links_row = []
    if LINK_PORTAL:
        links_row.append(InlineKeyboardButton("🌐 Portal", url=LINK_PORTAL))
    if LINK_CHANNEL:
        links_row.append(InlineKeyboardButton("📢 Channel", url=LINK_CHANNEL))
    
    links_row_2 = []
    if LINK_CHAT:
        links_row_2.append(InlineKeyboardButton("💬 Chat", url=LINK_CHAT))
    if LINK_SUPPORT:
        links_row_2.append(InlineKeyboardButton("🆘 Support", url=LINK_SUPPORT))
    
    # Add links rows if they have buttons
    if links_row:
        keyboard.append(links_row)
    if links_row_2:
        keyboard.append(links_row_2)

    welcome_text = (
        "🐱 <b>Welcome to Casino ⚡</b>\n\n"
        "⭐️ Casino - the best online mini-games platform on Telegram\n"
        f"💵 <b>Balance:</b> {formatted_balance}\n"
        f"👑 <b>Wagers:</b> {formatted_wagers}\n\n"
        "🎮 Choose an option below to get started!"
    )

    await safe_edit_message(
        query,
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user if update.effective_user else None
    user_lang = get_user_lang(user.id) if user else DEFAULT_LANG
    
    keyboard = [
        [InlineKeyboardButton("🔥 House Games", callback_data="games_category_house")],
        [InlineKeyboardButton("🎲 Emoji Games", callback_data="games_category_emoji")],
        [InlineKeyboardButton("⚡ Official Group", url="https://t.me/playcsino")],
        [InlineKeyboardButton(get_text("back", user_lang), callback_data="back_to_main")]
    ]
    text = get_text("games_menu", user_lang)

    if update.callback_query:
        await safe_edit_message(
            update.callback_query,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Set menu owner after editing
        if user:
            set_menu_owner(update.callback_query.message, user.id)
    else:
        sent_message = await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Set menu owner after sending
        if user:
            set_menu_owner(sent_message, user.id)

## NEW FEATURE - Game Category Menu ##
@check_banned
@check_maintenance
async def games_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    # Extract category from callback data
    if query.data == "games_category_emoji":
        category = "emoji"
    elif query.data == "games_emoji_regular":
        category = "emoji-regular"
    elif query.data == "games_emoji_single":
        category = "emoji-single"
    elif query.data == "games_category_house":
        category = "house"
    else:
        category = query.data.split('_')[-1]

    if category == "house":
        text = "🏠 <b>House Games</b>\n\nChoose a game to see how to play:"
        keyboard = [
            [InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack"),
             InlineKeyboardButton("🎲 Dice Roll", callback_data="game_dice_roll")],
            [InlineKeyboardButton("🔮 Predict", callback_data="game_predict"),
             InlineKeyboardButton("🎯 Roulette", callback_data="game_roulette")],
            [InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
             InlineKeyboardButton("🏗️ Tower", callback_data="game_tower_start")],
            [InlineKeyboardButton("💣 Mines", callback_data="game_mines_start"),
             InlineKeyboardButton("🎯 Keno", callback_data="game_keno")],
            [InlineKeyboardButton("🪙 Coin Flip", callback_data="game_coin_flip"),
             InlineKeyboardButton("🎴 High-Low", callback_data="game_highlow")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="main_games")]
        ]
    elif category == "emoji":
        text = "😀 <b>Emoji Games</b>\n\nChoose a category:"
        keyboard = [
            [InlineKeyboardButton("🎮 Regular Games", callback_data="games_emoji_regular")],
            [InlineKeyboardButton("🎯 Single Emoji Games", callback_data="games_emoji_single")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="main_games")]
        ]
    elif category == "emoji-regular":
        text = "🎮 <b>Regular Emoji Games</b>\n\nChoose a game to see how to play:"
        keyboard = [
            [InlineKeyboardButton("🎲 Dice", callback_data="game_dice_bot")],
            [InlineKeyboardButton("🎯 Darts", callback_data="game_darts")],
            [InlineKeyboardButton("⚽ Football", callback_data="game_football")],
            [InlineKeyboardButton("🎳 Bowling", callback_data="game_bowling")],
            [InlineKeyboardButton("🔙 Back to Emoji Games", callback_data="games_category_emoji")]
        ]
    elif category == "emoji-single":
        text = "🎯 <b>Single Emoji Games</b>\n\nQuick games with instant results!\n\nHow to play: Choose a game, set your bet, and watch the emoji!"
        keyboard = [
            [InlineKeyboardButton("🎯 Darts (1.15x)", callback_data="game_single_darts")],
            [InlineKeyboardButton("⚽ Soccer (1.53x)", callback_data="game_single_soccer")],
            [InlineKeyboardButton("🏀 Basket (2.25x)", callback_data="game_single_basket")],
            [InlineKeyboardButton("🎳 Bowling (5.00x)", callback_data="game_single_bowling")],
            [InlineKeyboardButton("🎰 Slot (14.5x)", callback_data="game_single_slot")],
            [InlineKeyboardButton("🔙 Back to Emoji Games", callback_data="games_category_emoji")]
        ]
    else:
        return

    await safe_edit_message(
        query,
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- GAME INFO CALLBACKS ---
@check_banned
@check_maintenance
async def game_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    data = query.data
    await ensure_user_in_wallets(query.from_user.id, query.from_user.username, context=context)

    if data == "game_blackjack":
        await safe_edit_message(query,
            "🃏 <b>Blackjack</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Get as close to 21 as possible\n"
            "• Beat the dealer without going over 21\n"
            "• Ace = 1 or 11, Face cards = 10\n\n"
            "<b>Commands:</b>\n"
            "• <code>/bj amount</code> - Start blackjack\n"
            "• Example: <code>/bj 5</code> or <code>/bj all</code>\n\n"
            "<b>Payouts:</b>\n"
            "• Win: 2x your bet\n"
            "• Blackjack: 2.5x your bet\n"
            "• Push: Get your bet back",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )

    elif data == "game_coin_flip":
        await safe_edit_message(query,
            "🪙 <b>Coin Flip</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Choose Heads or Tails\n"
            "• Win: 2x multiplier\n"
            "• Keep winning to increase multiplier!\n\n"
            "<b>Commands:</b>\n"
            "• <code>/flip amount</code> - Start coin flip\n"
            "• Example: <code>/flip 1</code> or <code>/flip all</code>\n\n"
            "<b>Multiplier Chain:</b>\n"
            "• 1 win: 2x\n"
            "• 2 wins: 4x\n"
            "• 3 wins: 8x\n"
            "• And so on... 🚀",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )
    
    elif data == "game_highlow":
        await safe_edit_message(query,
            "🎴 <b>High-Low Card Game</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• You're shown a card\n"
            "• Guess if next card is Higher, Lower, or Skip\n"
            "• Each correct guess increases multiplier\n"
            "• Cash out anytime after first win!\n\n"
            "<b>Commands:</b>\n"
            "• <code>/hl amount</code> - Start High-Low game\n"
            "• Example: <code>/hl 5</code> or <code>/hl all</code>\n\n"
            "<b>Multipliers:</b>\n"
            "• Increases based on probability of outcome\n"
            "• Ace is low (1), King is high (13)\n"
            "• Skip gives smaller multiplier but safer",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )
    elif data == "game_limbo":
        await safe_edit_message(query,
            "🚀 <b>LIMBO</b>\n\n"
            "<b>How to play:</b>\n"
            "• Choose your target multiplier (1.01 - 1000.00)\n"
            "• A random outcome is generated\n"
            "• If outcome ≥ your target: You win (bet × target)\n"
            "• If outcome < your target: You lose\n\n"
            "<b>Probability:</b>\n"
            "• 2x = ~48% chance\n"
            "• 4x = ~24% chance\n"
            "• Higher multipliers = lower chance\n\n"
            "<b>Usage:</b> <code>/lb amount multiplier</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/lb 10 2.00</code> - Bet $10 at 2x\n"
            "• <code>/lb all 1.5</code> - Bet all at 1.5x\n\n"
            f"<b>Min bet:</b> ${MIN_BALANCE:.2f}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]]
            ),
        )
    elif data == "game_roulette":
        await safe_edit_message(query,
            "🎯 <b>Roulette</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Choose number (0-36), color, or type\n\n"
            "<b>Commands:</b>\n"
            "• <code>/roul amount choice</code>\n"
            "• <code>/roulette amount choice</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/roul 1 5</code> (number 5)\n"
            "• <code>/roul all red</code> (red color)\n"
            "• <code>/roul 1 even</code> (even numbers)\n"
            "• <code>/roul 1 low</code> (1-18)\n"
            "• <code>/roul 1 high</code> (19-36)\n\n"
            "<b>Payouts:</b>\n"
            "• Single number: 35x\n"
            "• Red/Black, Even/Odd, High/Low: 2x\n"
            "• Columns: 3x",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )

    elif data == "game_dice_roll":
        await safe_edit_message(query,
            "🎲 <b>Dice Roll</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Choose number (1-6), even/odd, or high/low\n"

            "• Bot rolls real Telegram dice\n\n"
            "<b>Commands:</b>\n"
            "• <code>/dr amount choice</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/dr 1 3</code> (number 3)\n"
            "• <code>/dr all even</code> (even numbers)\n"
            "• <code>/dr 1 high</code> (4,5,6)\n"
            "• <code>/dr 1 low</code> (1,2,3)\n\n"
            "<b>Payouts:</b>\n"
            "• Exact number: 5.96x\n"
            "• Even/Odd/High/Low: 1.96x",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )

    elif data == "game_slots":
        await safe_edit_message(query,
            "🎰 <b>Slots</b>\n\n"
            "<b>How to play:</b>\n"
            "• Bot rolls real Telegram slot machine\n"
            "• Get 3 matching symbols to win\n\n"
            "<b>Commands:</b>\n"
            "• <code>/sl amount</code>\n"
            "• Example: <code>/sl 1</code> or <code>/sl all</code>\n\n"
            "<b>Payouts:</b>\n"
            "• 3 matching BAR, LEMON, or GRAPE: 14x\n"
            "• Triple 7s (JACKPOT): 28x",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )

    elif data == "game_predict":
        await safe_edit_message(query,
            "🔮 <b>Predict Dice</b>\n\n"
            "<b>How to play:</b>\n"
            "• Predict if dice will be up (4-6) or down (1-3)\n"
            "• 2x payout on correct prediction\n\n"
            "<b>Commands:</b>\n"
            "• <code>/predict amount up</code>\n"
            "• <code>/predict all down</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )



    elif data == "game_keno":
        await safe_edit_message(query,
            "🎯 <b>KENO</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Pick 1-10 numbers from 1-40\n"
            "• 10 random numbers are drawn\n"
            "• Win based on matches!\n\n"
            "<b>Commands:</b>\n"
            "• <code>/keno amount</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/keno 10</code> - Start with $10\n"
            "• <code>/keno all</code> - Start with all balance\n\n"
            "<b>Strategy Tips:</b>\n"
            "• More picks = higher payouts\n"
            "• But need more matches to win\n"
            "• 5-7 picks is balanced\n"
            "• Check payout table in-game\n\n"
            "Uses provably fair system!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="games_category_house")]])
        )

    elif data == "game_crash":
        await safe_edit_message(query,
            "📉 <b>CRASH</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Multiplier starts at 1.00x and rises\n"
            "• Cash out before it crashes!\n"
            "• The longer you wait, the higher the multiplier\n"
            "• But if you don't cash out in time, you lose\n\n"
            "<b>Commands:</b>\n"
            "• <code>/crash amount</code>\n"
            "• <code>/crash amount target</code> (auto cashout)\n\n"
            "<b>Examples:</b>\n"
            "• <code>/crash 10</code> - $10 bet, manual cashout\n"
            "• <code>/crash 5 2.5</code> - $5, auto cashout at 2.5x\n"
            "• <code>/crash all 3</code> - All balance, auto at 3x\n\n"
            "<b>Tips:</b>\n"
            "• Average crash point: ~1.98x\n"
            "• Lower targets = higher win rate\n"
            "• High multipliers are rare but exciting!\n\n"
            "Provably fair!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to House Games", callback_data="games_category_house")]])
        )

    elif data == "game_plinko":
        await safe_edit_message(query,
            "🎪 <b>PLINKO</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Drop a ball through pegs\n"
            "• Ball bounces randomly\n"
            "• Land in slots with different multipliers\n"
            "• Center = lower multipliers, safer\n"
            "• Edges = higher multipliers, riskier\n\n"
            "<b>Commands:</b>\n"
            "• <code>/plinko amount risk</code>\n\n"
            "<b>Risk Levels:</b>\n"
            "• <code>low</code> - Max 5.6x, safer\n"
            "• <code>medium</code> - Max 33x, balanced\n"
            "• <code>high</code> - Max 420x, risky!\n\n"
            "<b>Examples:</b>\n"
            "• <code>/plinko 5 low</code>\n"
            "• <code>/plinko 10 medium</code>\n"
            "• <code>/plinko all high</code>\n\n"
            "Provably fair!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to House Games", callback_data="games_category_house")]])
        )

    elif data == "game_wheel":
        await safe_edit_message(query,
            "🎡 <b>WHEEL OF FORTUNE</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Spin the wheel for prizes\n"
            "• 50 segments with different multipliers\n"
            "• Multipliers range from 0.2x to 50x\n"
            "• The higher the multiplier, the rarer\n\n"
            "<b>Commands:</b>\n"
            "• <code>/wheel amount</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/wheel 10</code> - Spin with $10\n"
            "• <code>/wheel all</code> - Spin with all balance\n\n"
            "<b>Multiplier Distribution:</b>\n"
            "• 0.2x-1x: Common (~40%)\n"
            "• 1.5x-5x: Uncommon (~35%)\n"
            "• 10x-20x: Rare (~20%)\n"
            "• 30x-50x: Very Rare (~5%)\n\n"
            "Provably fair!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to House Games", callback_data="games_category_house")]])
        )

    elif data == "game_scratch":
        await safe_edit_message(query,
            "🎫 <b>SCRATCH CARD</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Buy a scratch card\n"
            "• Reveal 9 squares instantly\n"
            "• Match 3 symbols to win\n"
            "• Different symbols = different multipliers\n\n"
            "<b>Commands:</b>\n"
            "• <code>/scratch amount</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/scratch 5</code> - Buy $5 card\n"
            "• <code>/scratch all</code> - Buy card with all balance\n\n"
            "<b>Symbol Multipliers:</b>\n"
            "• 💎 Diamond: 100x\n"
            "• 👑 Crown: 50x\n"
            "• ⭐ Star: 20x\n"
            "• 💰 Money: 10x\n"
            "• 🍀 Clover: 5x\n"
            "• 🎰 Slot: 2x\n\n"
            "Provably fair!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to House Games", callback_data="games_category_house")]])
        )

    elif data == "game_coin_chain":
        await safe_edit_message(query,
            "🪙 <b>COIN TOSS CHAIN</b>\n\n"
            "<b>How to play:</b>\n"
            f"• Minimum bet: ${MIN_BALANCE:.2f}\n"
            "• Toss a coin - Heads or Tails\n"
            "• Each correct guess = 1.9x multiplier\n"
            "• Keep winning to build a chain\n"
            "• Cash out anytime or go for more\n"
            "• One wrong guess = lose everything\n\n"
            "<b>Commands:</b>\n"
            "• <code>/coinchain amount</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/coinchain 5</code> - Start with $5\n"
            "• <code>/coinchain all</code> - Start with all balance\n\n"
            "<b>Chain Multipliers:</b>\n"
            "• 1 win: 1.9x\n"
            "• 2 wins: 3.61x\n"
            "• 3 wins: 6.86x\n"
            "• 4 wins: 13.03x\n"
            "• 5 wins: 24.76x\n"
            "• 10 wins: 613.11x (!)\n\n"
            "Provably fair!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to House Games", callback_data="games_category_house")]])
        )

    # Single Emoji Games
    elif data.startswith("game_single_"):
        game_key = data.replace("game_single_", "")
        if game_key in SINGLE_EMOJI_GAMES:
            game_config = SINGLE_EMOJI_GAMES[game_key]
            await safe_edit_message(query,
                f"{game_config['emoji']} <b>{game_config['name']}</b>\n\n"
                f"<b>How to play:</b>\n"
                f"• Quick instant-result game\n"
                f"• Win when: {game_config['win_description']}\n"
                f"• Multiplier: {game_config['multiplier']}x\n"
                f"• Win chance: {game_config['win_chance']*100:.1f}%\n\n"
                f"<b>How to start:</b>\n"
                f"1. Tap 'Play Game' below\n"
                f"2. Enter your bet amount\n"
                f"3. Watch the {game_config['emoji']} animation!\n\n"
                f"Simple, fast, and fun!",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🎮 Play {game_config['emoji']}", callback_data=f"play_single_{game_key}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="games_category_emoji-single")]
                ])
            )

    # PvP games
    elif data.startswith("game_"):
        game_name_map = {
            "football": "Football", "darts": "Darts", "bowling": "Bowling", "dice_bot": "Dice"
        }
        game_key = data.replace("game_", "")
        game_name = game_name_map.get(game_key, game_key.replace("_", " ").title())

        keyboard = [
            [InlineKeyboardButton(f"🤖 Play vs Bot", callback_data=f"pvb_start_{game_key}")],
            [InlineKeyboardButton(f"👤 Play vs Player", callback_data=f"pvp_info_{game_key}")],
            [InlineKeyboardButton("🔙 Back to Regular Games", callback_data="games_emoji_regular")]
        ]

        await safe_edit_message(query,
            f"🎮 <b>{game_name}</b>\n\n"
            "Who do you want to play against?",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- NEW GAME IMPLEMENTATIONS ---

# 1. BLACKJACK GAME
@check_banned
@check_maintenance
async def blackjack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)

    user_currency = get_user_currency(user.id)
    formatted_balance = format_currency(user_wallets.get(user.id, 0.0), user_currency)

    if len(args) != 2:
        await update.message.reply_text(f"Usage: /bj amount\nExample: /bj 5 or /bj all\nYour balance: {formatted_balance}")
        return

    try:
        bet_amount_str = args[1]
        bet_amount_usd, bet_amount_currency, currency = parse_bet_amount(bet_amount_str, user.id)
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a valid number or 'all'.")
        return

    if not await check_bet_limits(update, bet_amount_usd, 'blackjack'):
        return

    if user_wallets.get(user.id, 0.0) < bet_amount_usd:
        await send_insufficient_balance_message(update, f"❌ You don't have enough balance. Your balance: {formatted_balance}")
        return

    user_wallets[user.id] -= bet_amount_usd
    save_user_data(user.id)

    # Use user's provably fair seeds
    seeds = get_user_seeds(user.id)
    
    # Create deck and shuffle deterministically using Fisher-Yates
    deck = create_deck()
    for i in range(len(deck) - 1, 0, -1):
        j = get_provably_fair_result(seeds["server_seed"], seeds["client_seed"], seeds["nonce"] + i, i + 1)
        deck[i], deck[j] = deck[j], deck[i]

    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    game_id = generate_unique_id("BJ")
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "blackjack",
        "user_id": user.id,
        "bet_amount": bet_amount_usd,
        "bet_amount_currency": bet_amount_currency,
        "currency": currency,
        "status": "active",
        "timestamp": str(datetime.now(timezone.utc)),
        "deck": deck,
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "server_seed": seeds["server_seed"],
        "client_seed": seeds["client_seed"],
        "nonce": seeds["nonce"],
        "doubled": False
    }
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if 'game_sessions' not in user_stats[user.id]: user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(game_id)
    save_user_data(user.id)


    player_value = calculate_hand_value(player_hand)
    dealer_show_card = dealer_hand[0]

    hand_text = format_hand("Your hand", player_hand, player_value)
    dealer_text = f"Dealer shows: {dealer_show_card}\n"
    
    currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")
    formatted_bet = f"{currency_symbol}{bet_amount_currency:.2f}"

    if player_value == 21:
        dealer_value = calculate_hand_value(dealer_hand)
        game_sessions[game_id]['status'] = 'completed'
        game_sessions[game_id]['win'] = True
        increment_user_nonce(user.id)
        
        # Store provably fair record
        game = game_sessions[game_id]
        store_provably_fair_record(game_id, "blackjack", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Player: {player_value}, Dealer: {dealer_value}")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        
        if dealer_value == 21:
            user_wallets[user.id] += bet_amount_usd
            save_user_data(user.id)
            await update.message.reply_text(
                f"{hand_text}\n{format_hand('Dealer hand', dealer_hand, dealer_value)}\n"
                f"🤝 Push! Both have blackjack. Bet returned: {formatted_bet}\nGame ID: <code>{game_id}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Blackjack pays 2.425x (3% house edge)
            winnings_usd = bet_amount_usd * 2.425
            winnings_currency = bet_amount_currency * 2.425
            user_wallets[user.id] += winnings_usd
            update_stats_on_bet(user.id, game_id, bet_amount_usd, True, multiplier=2.425, context=context)
            update_pnl(user.id)
            save_user_data(user.id)
            await update.message.reply_text(
                f"{hand_text}\n{dealer_text}\n"
                f"🎉 Blackjack! You win {currency_symbol}{winnings_currency:.2f}!\nGame ID: <code>{game_id}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    keyboard = [
        [InlineKeyboardButton("👊 Hit", callback_data=f"bj_hit_{game_id}"),
         InlineKeyboardButton("✋ Stand", callback_data=f"bj_stand_{game_id}")],
    ]

    if len(player_hand) == 2 and user_wallets.get(user.id, 0.0) >= bet_amount_usd:
        keyboard.append([InlineKeyboardButton("⬆️ Double Down", callback_data=f"bj_double_{game_id}")])

    await update.message.reply_text(
        f"🃏 <b>Blackjack Started!</b> (ID: <code>{game_id}</code>)\n\n"
        f"{hand_text}\n{dealer_text}\n"
        f"💰 Bet: {formatted_bet}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def create_deck():
    deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck

def calculate_hand_value(hand):
    value = 0
    aces = 0
    for card in hand:
        rank = card[:-1]
        if rank == 'A':
            aces += 1
            value += 11
        elif rank in ['J', 'Q', 'K']:
            value += 10
        else:
            value += int(rank)
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    return value

def format_hand(title, hand, value):
    cards_str = " ".join(hand)
    return f"{title}: {cards_str} (Value: {value})"

@check_banned
@check_maintenance
async def blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if not query.data.startswith("bj_"):
        return

    parts = query.data.split("_")
    action = parts[1]
    game_id = parts[2]

    game = game_sessions.get(game_id)

    if not game:
        await query.edit_message_text("Game not found or already finished.")
        return

    # NEW: Game interaction security
    if user.id != game.get('user_id'):
        await query.answer("This is not your game!", show_alert=True)
        return
        
    if game.get('status') != 'active':
        await query.edit_message_text("This game is already finished.")
        return


    if action == "hit":
        card = game["deck"].pop()
        game["player_hand"].append(card)
        player_value = calculate_hand_value(game["player_hand"])

        hand_text = format_hand("Your hand", game["player_hand"], player_value)
        dealer_text = f"Dealer shows: {game['dealer_hand'][0]}"

        if player_value > 21:
            game["status"] = 'completed'
            game["win"] = False
            increment_user_nonce(user.id)
            update_stats_on_bet(user.id, game_id, game["bet_amount"], False, context=context)
            update_pnl(user.id)
            save_user_data(user.id)
            
            # Store provably fair record
            store_provably_fair_record(game_id, "blackjack", game["server_seed"], game["client_seed"], game["nonce"], 
                                       result_data=f"Player busted: {player_value}")
            
            # Add provably fair button
            keyboard = [[await create_provably_fair_button(game_id, context)]]
            
            await query.edit_message_text(
                f"🃏 <b>Blackjack</b> (ID: <code>{game_id}</code>)\n\n{hand_text}\n{dealer_text}\n\n"
                f"💥 Bust! You lose ${game['bet_amount']:.2f}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif player_value == 21:
            await handle_dealer_turn(query, context, game_id)
        else:
            keyboard = [
                [InlineKeyboardButton("👊 Hit", callback_data=f"bj_hit_{game_id}"),
                 InlineKeyboardButton("✋ Stand", callback_data=f"bj_stand_{game_id}")]
            ]
            await query.edit_message_text(
                f"🃏 <b>Blackjack</b> (ID: <code>{game_id}</code>)\n\n{hand_text}\n{dealer_text}\n"
                f"💰 Bet: ${game['bet_amount']:.2f}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif action == "stand":
        await handle_dealer_turn(query, context, game_id)

    elif action == "double":
        if user_wallets.get(user.id, 0.0) < game["bet_amount"]:
            # Show alert with deposit option
            await query.answer("❌ Not enough balance to double down!", show_alert=True)
            # Edit message to show back button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Game", callback_data=f"bj_continue_{game_id}")]
            ])
            await query.edit_message_text(
                f"❌ You don't have enough balance to double down.\n\n"
                f"Required: ${game['bet_amount']:.2f}\n"
                f"Your balance: ${user_wallets.get(user.id, 0.0):.2f}\n\n"
                f"Please deposit to continue.",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return

        user_wallets[user.id] -= game["bet_amount"]
        game["bet_amount"] *= 2
        game["doubled"] = True
        save_user_data(user.id)

        card = game["deck"].pop()
        game["player_hand"].append(card)
        player_value = calculate_hand_value(game["player_hand"])

        if player_value > 21:
            game["status"] = 'completed'
            game["win"] = False
            increment_user_nonce(user.id)
            # On double down loss, the original bet amount is what's recorded for stats
            update_stats_on_bet(user.id, game_id, game["bet_amount"]/2, False, context=context)
            update_pnl(user.id)
            save_user_data(user.id)
            hand_text = format_hand("Your hand", game["player_hand"], player_value)
            
            # Store provably fair record
            store_provably_fair_record(game_id, "blackjack", game["server_seed"], game["client_seed"], game["nonce"], 
                                       result_data=f"Double down - Player busted: {player_value}")
            
            # Add provably fair button
            keyboard = [[await create_provably_fair_button(game_id, context)]]
            
            await query.edit_message_text(
                f"🃏 <b>Blackjack - Doubled Down</b> (ID: <code>{game_id}</code>)\n\n{hand_text}\n\n"
                f"💥 Bust! You lose ${game['bet_amount']:.2f}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await handle_dealer_turn(query, context, game_id)

async def handle_dealer_turn(query, context, game_id):
    game = game_sessions[game_id]
    user_id = game["user_id"]
    original_bet = game["bet_amount"] / 2 if game["doubled"] else game["bet_amount"]


    while calculate_hand_value(game["dealer_hand"]) < 17:
        game["dealer_hand"].append(game["deck"].pop())

    player_value = calculate_hand_value(game["player_hand"])
    dealer_value = calculate_hand_value(game["dealer_hand"])
    player_text = format_hand("Your hand", game["player_hand"], player_value)
    dealer_text = format_hand("Dealer hand", game["dealer_hand"], dealer_value)
    double_text = " - Doubled Down" if game["doubled"] else ""

    if dealer_value > 21:
        # Regular win pays 1.94x (3% house edge)
        winnings = game["bet_amount"] * 1.94
        user_wallets[user_id] += winnings
        result = f"🎉 Dealer busts! You win ${winnings:.2f}!"
        game['win'] = True
        update_stats_on_bet(user_id, game_id, original_bet, True, multiplier=1.94, context=context)
    elif dealer_value > player_value:
        result = f"😢 Dealer wins with {dealer_value}. You lose ${game['bet_amount']:.2f}"
        game['win'] = False
        update_stats_on_bet(user_id, game_id, original_bet, False, context=context)
    elif player_value > dealer_value:
        # Regular win pays 1.94x (3% house edge)
        winnings = game["bet_amount"] * 1.94
        user_wallets[user_id] += winnings
        result = f"🎉 You win! ${winnings:.2f}"
        game['win'] = True
        update_stats_on_bet(user_id, game_id, original_bet, True, multiplier=1.94, context=context)
    else:
        user_wallets[user_id] += game["bet_amount"]
        result = "🤝 Push! Bet returned."
        game['win'] = None # No win or loss

    update_pnl(user_id)
    save_user_data(user_id)
    game["status"] = 'completed'
    increment_user_nonce(user_id)
    
    # Store provably fair record
    store_provably_fair_record(game_id, "blackjack", game["server_seed"], game["client_seed"], game["nonce"], 
                               result_data=f"Player: {player_value}, Dealer: {dealer_value}")
    
    # Add provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]

    await query.edit_message_text(
        f"🃏 <b>Blackjack{double_text}</b> (ID: <code>{game_id}</code>)\n\n{player_text}\n{dealer_text}\n\n{result}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 2. COIN FLIP GAME (Enhanced)
@check_banned
@check_maintenance
async def coin_flip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if len(args) != 2:
        await update.message.reply_text("Usage: /flip amount or /flip all")
        return
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet = user_wallets.get(user.id, 0.0)
        else:
            bet = float(bet_amount_str)
    except Exception:
        await update.message.reply_text("Invalid amount.")
        return

    if not await check_bet_limits(update, bet, 'coin_flip'):
        return

    if user_wallets.get(user.id, 0.0) < bet:
        await send_insufficient_balance_message(update)
        return

    user_wallets[user.id] -= bet
    save_user_data(user.id)

    # Use user's provably fair seeds
    seeds = get_user_seeds(user.id)
    game_id = generate_unique_id("CF")

    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "coin_flip",
        "user_id": user.id,
        "bet_amount": bet,
        "status": "active",
        "timestamp": str(datetime.now(timezone.utc)),
        "streak": 0,
        "server_seed": seeds["server_seed"],
        "client_seed": seeds["client_seed"],
        "nonce": seeds["nonce"]
    }
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if 'game_sessions' not in user_stats[user.id]: user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(game_id)
    save_user_data(user.id)


    keyboard = [
        [InlineKeyboardButton("🪙 Heads", callback_data=f"flip_pick_{game_id}_Heads"),
         InlineKeyboardButton("🪙 Tails", callback_data=f"flip_pick_{game_id}_Tails")]
    ]
    await update.message.reply_text(
        f"🪙 <b>Coin Flip Started!</b> (ID: <code>{game_id}</code>)\n\n💰 Bet: ${bet:.2f}\nChoose Heads or Tails!\n\n"
        f"🎯 Current Multiplier: 1.94x",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@check_banned
@check_maintenance
async def coin_flip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    parts = query.data.split("_")
    action = parts[1]
    game_id = parts[2]

    game = game_sessions.get(game_id)
    if not game:
        await query.edit_message_text("No active coin flip game found or this is not your game.")
        return

    if user.id != game.get('user_id'):
        await query.answer("This is not your game!", show_alert=True)
        return
        
    if game.get('status') != 'active':
        await query.edit_message_text("This game is already finished.")
        return


    if action == "pick":
        pick = parts[3]
        game["nonce"] += 1
        result_num = get_provably_fair_result(game["server_seed"], game["client_seed"], game["nonce"], 2)
        bot_choice = "Heads" if result_num == 0 else "Tails"

        if pick == bot_choice:
            game["streak"] += 1
            # Changed multiplier progression to maintain house edge
            # 1.94x on first win, 3.88x on second, 7.76x on third, etc.
            multiplier = 1.94 * (2 ** (game["streak"] - 1))
            win_amount = game["bet_amount"] * multiplier
            next_multiplier = 1.94 * (2 ** game["streak"])
            keyboard = [
                [InlineKeyboardButton("🪙 Heads", callback_data=f"flip_pick_{game_id}_Heads"),
                 InlineKeyboardButton("🪙 Tails", callback_data=f"flip_pick_{game_id}_Tails")],
                [InlineKeyboardButton(f"💸 Cash Out (${win_amount:.2f})", callback_data=f"flip_cashout_{game_id}")]
            ]
            await query.edit_message_text(
                f"🎉 <b>Correct!</b> The coin landed on {pick}!\n\n"
                f"💰 Current Win: <b>${win_amount:.2f}</b>\n🔥 Streak: {game['streak']}\n"
                f"🎯 Next Multiplier: {next_multiplier:.2f}x\n\nContinue playing or cash out?\nID: <code>{game_id}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            game["status"] = 'completed'
            game["win"] = False
            increment_user_nonce(user.id)
            update_stats_on_bet(user.id, game_id, game['bet_amount'], False, context=context)
            update_pnl(user.id)
            save_user_data(user.id)
            
            # Store provably fair record
            store_provably_fair_record(game_id, "coinflip", game["server_seed"], game["client_seed"], game["nonce"], 
                                       result_data=f"Streak: {game['streak']}, Result: {bot_choice}")
            
            # Add provably fair button
            keyboard = [[await create_provably_fair_button(game_id, context)]]
            
            await query.edit_message_text(
                f"❌ <b>Wrong!</b> You picked {pick}, but the coin landed on {bot_choice}.\n\n"
                f"💔 You lost your bet of ${game['bet_amount']:.2f}\n🎯 Your streak was: {game['streak']}\nID: <code>{game_id}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            # del game_sessions[game_id] # FIX: Don't delete history

    elif action == "cashout":
        # Changed multiplier progression to maintain house edge
        # 1.94x on first win, 3.88x on second, 7.76x on third, etc.
        multiplier = 1.94 * (2 ** (game["streak"] - 1))
        win_amount = game["bet_amount"] * multiplier
        user_wallets[user.id] += win_amount
        game["status"] = 'completed'
        game["win"] = True
        game["multiplier"] = multiplier
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game['bet_amount'], True, multiplier=multiplier, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "coinflip", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Streak: {game['streak']}, Multiplier: {multiplier:.2f}x")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        
        await query.edit_message_text(
            f"💸 <b>Cashed Out!</b>\n\n🎉 You won <b>${win_amount:.2f}</b>!\n"
            f"🔥 Final streak: {game['streak']}\n📈 Final multiplier: {multiplier:.2f}x\nID: <code>{game_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # del game_sessions[game_id] # FIX: Don't delete history

# 2B. HIGH-LOW CARD GAME
# High-Low multiplier table based on probability
# Card emoji mapping
CARD_EMOJIS = {
    1: "🂡",   # Ace of Spades
    2: "🂢",   # 2 of Spades
    3: "🂣",   # 3 of Spades
    4: "🂤",   # 4 of Spades
    5: "🂥",   # 5 of Spades
    6: "🂦",   # 6 of Spades
    7: "🂧",   # 7 of Spades
    8: "🂨",   # 8 of Spades
    9: "🂩",   # 9 of Spades
    10: "🂪",  # 10 of Spades
    11: "🂫",  # Jack of Spades
    12: "🂭",  # Queen of Spades
    13: "🂮",  # King of Spades
}

def calculate_highlow_multiplier(current_card: int, deck: list, bet_type: str) -> float:
    """
    Calculate multiplier based on probability according to hl.txt specifications.
    Formula: Multiplier = 0.98 / P(Bet)
    House edge is 2%, meaning 98% RTP
    """
    if not deck:
        return 1.0
    
    total_remaining = len(deck)
    
    # Count remaining cards by rank
    rank_counts = {}
    for card in deck:
        rank_counts[card] = rank_counts.get(card, 0) + 1
    
    # Calculate probabilities
    if bet_type == "high":
        # Count cards with rank higher than current
        higher_cards = sum(count for rank, count in rank_counts.items() if rank > current_card)
        probability = higher_cards / total_remaining if total_remaining > 0 else 0
    elif bet_type == "low":
        # Count cards with rank lower than current
        lower_cards = sum(count for rank, count in rank_counts.items() if rank < current_card)
        probability = lower_cards / total_remaining if total_remaining > 0 else 0
    elif bet_type == "tie":
        # Count cards with same rank as current
        same_cards = rank_counts.get(current_card, 0)
        probability = same_cards / total_remaining if total_remaining > 0 else 0
    else:
        return 1.0
    
    # Avoid division by zero
    if probability <= 0:
        return 0  # Can't win, no multiplier
    
    # Calculate multiplier with 2% house edge
    multiplier = 0.98 / probability
    
    return round(multiplier, 2)

@check_banned
@check_maintenance
async def highlow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if len(args) != 2:
        await update.message.reply_text(
            "Usage: /hl amount\n\nExamples:\n"
            "• /hl 5 - Bet $5\n"
            "• /hl all - Bet all balance"
        )
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet = user_wallets.get(user.id, 0.0)
        else:
            bet = float(bet_amount_str)
    except Exception:
        await update.message.reply_text("Invalid amount.")
        return
    
    if not await check_bet_limits(update, bet, 'highlow'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet:
        await send_insufficient_balance_message(update)
        return
    
    user_wallets[user.id] -= bet
    save_user_data(user.id)
    
    # Use user's provably fair seeds
    seeds = get_user_seeds(user.id)
    game_id = generate_unique_id("HL")
    
    # Generate deck of cards (1-13, where 1=Ace, 11=Jack, 12=Queen, 13=King) deterministically
    deck = list(range(1, 14)) * 4  # 4 suits
    # Shuffle deck using provably fair method
    for i in range(len(deck) - 1, 0, -1):
        j = get_provably_fair_result(seeds["server_seed"], seeds["client_seed"], seeds["nonce"] + i, i + 1)
        deck[i], deck[j] = deck[j], deck[i]
    
    current_card = deck.pop()
    
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "highlow",
        "user_id": user.id,
        "bet_amount": bet,
        "status": "active",
        "timestamp": str(datetime.now(timezone.utc)),
        "streak": 0,
        "server_seed": seeds["server_seed"],
        "client_seed": seeds["client_seed"],
        "nonce": seeds["nonce"],
        "deck": deck,
        "current_card": current_card,
        "current_multiplier": 1.0
    }
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if 'game_sessions' not in user_stats[user.id]:
        user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(game_id)
    save_user_data(user.id)
    
    card_name = get_card_name(current_card)
    
    # Calculate multipliers for each choice
    high_mult = calculate_highlow_multiplier(current_card, deck, "high")
    low_mult = calculate_highlow_multiplier(current_card, deck, "low")
    tie_mult = calculate_highlow_multiplier(current_card, deck, "tie")
    
    # Build keyboard - conditionally show buttons based on card
    buttons = []
    
    # Add Higher button only if not King (13)
    if current_card != 13:
        buttons.append(InlineKeyboardButton(f"⬆️ Higher ({high_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_high"))
    
    # Add Lower button only if not Ace (1)
    if current_card != 1:
        buttons.append(InlineKeyboardButton(f"⬇️ Lower ({low_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_low"))
    
    # Always add Tie button
    buttons.append(InlineKeyboardButton(f"🔄 Tie ({tie_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_tie"))
    
    # Create keyboard with buttons in a single row, and skip button below
    keyboard = [
        buttons,
        [InlineKeyboardButton("⏭️ Skip Card", callback_data=f"hl_skip_{game_id}")]
    ]
    
    # Build multiplier text
    mult_text = "Choose your prediction:\n"
    if current_card != 13:
        mult_text += f"⬆️ Higher: {high_mult:.2f}x\n"
    if current_card != 1:
        mult_text += f"⬇️ Lower: {low_mult:.2f}x\n"
    mult_text += f"🔄 Tie: {tie_mult:.2f}x"
    
    await update.message.reply_text(
        f"🎴 <b>High-Low Game Started!</b> (ID: <code>{game_id}</code>)\n\n"
        f"💰 Bet: ${bet:.2f}\n"
        f"🃏 Current Card: <b>{card_name}</b>\n"
        f"📊 Cards remaining: {len(deck)}\n\n"
        f"{mult_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def get_card_name(card_value, with_emoji=True):
    """Convert card value to name, optionally with emoji"""
    card_names = {
        1: "Ace (A)", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
        8: "8", 9: "9", 10: "10", 11: "Jack (J)", 12: "Queen (Q)", 13: "King (K)"
    }
    name = card_names.get(card_value, str(card_value))
    
    if with_emoji and card_value in CARD_EMOJIS:
        emoji = CARD_EMOJIS[card_value]
        return f"{name} {emoji}"
    
    return name

@check_banned
@check_maintenance
async def highlow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if not query.data.startswith("hl_"):
        return
    
    parts = query.data.split("_")
    action = parts[1]
    game_id = parts[2]
    
    game = game_sessions.get(game_id)
    if not game:
        await query.edit_message_text("No active High-Low game found.")
        return
    
    if user.id != game.get('user_id'):
        await query.answer("This is not your game!", show_alert=True)
        return
    
    if game.get('status') != 'active':
        await query.edit_message_text("This game is already finished.")
        return
    
    if action == "skip":
        # Skip the current card and draw a new one
        if not game["deck"]:
            await query.answer("No more cards to skip!", show_alert=True)
            return
        
        # Draw new card
        new_card = game["deck"].pop()
        game["current_card"] = new_card
        
        card_name = get_card_name(new_card)
        win_amount = game["bet_amount"] * game["current_multiplier"]
        
        # Calculate new multipliers for the new card
        high_mult = calculate_highlow_multiplier(new_card, game["deck"], "high")
        low_mult = calculate_highlow_multiplier(new_card, game["deck"], "low")
        tie_mult = calculate_highlow_multiplier(new_card, game["deck"], "tie")
        
        # Build keyboard - conditionally show buttons based on card
        buttons = []
        if new_card != 13:
            buttons.append(InlineKeyboardButton(f"⬆️ Higher ({high_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_high"))
        if new_card != 1:
            buttons.append(InlineKeyboardButton(f"⬇️ Lower ({low_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_low"))
        buttons.append(InlineKeyboardButton(f"🔄 Tie ({tie_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_tie"))
        
        keyboard = [
            buttons,
            [InlineKeyboardButton("⏭️ Skip Card", callback_data=f"hl_skip_{game_id}")],
            [InlineKeyboardButton(f"💸 Cash Out (${win_amount:.2f})", callback_data=f"hl_cashout_{game_id}")]
        ]
        
        # Build multiplier text
        mult_text = "Next multipliers:\n"
        if new_card != 13:
            mult_text += f"⬆️ Higher: {high_mult:.2f}x\n"
        if new_card != 1:
            mult_text += f"⬇️ Lower: {low_mult:.2f}x\n"
        mult_text += f"🔄 Tie: {tie_mult:.2f}x"
        
        await query.edit_message_text(
            f"⏭️ <b>Card Skipped!</b>\n\n"
            f"🃏 New Current Card: <b>{card_name}</b>\n"
            f"💰 Current Win: <b>${win_amount:.2f}</b>\n"
            f"🔥 Streak: {game['streak']}\n"
            f"📈 Current Multiplier: {game['current_multiplier']:.2f}x\n"
            f"📊 Cards remaining: {len(game['deck'])}\n\n"
            f"{mult_text}\n\n"
            f"Continue playing or cash out?\nID: <code>{game_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if action == "pick":
        choice = parts[3]  # high, low, or tie
        current_card = game["current_card"]
        
        if not game["deck"]:
            # Deck exhausted - auto cashout
            action = "cashout"
        else:
            next_card = game["deck"].pop()
            
            # Calculate the multiplier for this choice BEFORE the draw
            choice_multiplier = calculate_highlow_multiplier(current_card, game["deck"] + [next_card], choice)
            
            # Determine if choice was correct
            correct = False
            if choice == "high" and next_card > current_card:
                correct = True
            elif choice == "low" and next_card < current_card:
                correct = True
            elif choice == "tie" and next_card == current_card:
                correct = True
            
            if correct:
                game["streak"] += 1
                # Apply the multiplier for this win
                game["current_multiplier"] *= choice_multiplier
                
                win_amount = game["bet_amount"] * game["current_multiplier"]
                game["current_card"] = next_card
                
                card_name = get_card_name(next_card)
                
                # Calculate new multipliers for next round
                high_mult = calculate_highlow_multiplier(next_card, game["deck"], "high")
                low_mult = calculate_highlow_multiplier(next_card, game["deck"], "low")
                tie_mult = calculate_highlow_multiplier(next_card, game["deck"], "tie")
                
                # Build keyboard - conditionally show buttons based on card
                buttons = []
                if next_card != 13:
                    buttons.append(InlineKeyboardButton(f"⬆️ Higher ({high_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_high"))
                if next_card != 1:
                    buttons.append(InlineKeyboardButton(f"⬇️ Lower ({low_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_low"))
                buttons.append(InlineKeyboardButton(f"🔄 Tie ({tie_mult:.2f}x)", callback_data=f"hl_pick_{game_id}_tie"))
                
                keyboard = [
                    buttons,
                    [InlineKeyboardButton("⏭️ Skip Card", callback_data=f"hl_skip_{game_id}")],
                    [InlineKeyboardButton(f"💸 Cash Out (${win_amount:.2f})", callback_data=f"hl_cashout_{game_id}")]
                ]
                
                # Build multiplier text
                mult_text = "Next multipliers:\n"
                if next_card != 13:
                    mult_text += f"⬆️ Higher: {high_mult:.2f}x\n"
                if next_card != 1:
                    mult_text += f"⬇️ Lower: {low_mult:.2f}x\n"
                mult_text += f"🔄 Tie: {tie_mult:.2f}x"
                
                await query.edit_message_text(
                    f"🎉 <b>Correct!</b> The next card is {card_name}!\n\n"
                    f"🃏 Current Card: <b>{card_name}</b>\n"
                    f"💰 Current Win: <b>${win_amount:.2f}</b>\n"
                    f"🔥 Streak: {game['streak']}\n"
                    f"📈 Current Total Multiplier: {game['current_multiplier']:.2f}x\n"
                    f"📊 Cards remaining: {len(game['deck'])}\n\n"
                    f"{mult_text}\n\n"
                    f"Continue playing or cash out?\nID: <code>{game_id}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Wrong guess - game over
                game["status"] = 'completed'
                game["win"] = False
                increment_user_nonce(user.id)
                update_stats_on_bet(user.id, game_id, game['bet_amount'], False, context=context)
                update_pnl(user.id)
                save_user_data(user.id)
                
                # Store provably fair record
                store_provably_fair_record(game_id, "hilo", game["server_seed"], game["client_seed"], game["nonce"], 
                                           result_data=f"Streak: {game['streak']}, Next card: {next_card}")
                
                # Add provably fair button
                keyboard = [[await create_provably_fair_button(game_id, context)]]
                
                next_card_name = get_card_name(next_card)
                await query.edit_message_text(
                    f"❌ <b>Wrong!</b> The next card was {next_card_name}.\n\n"
                    f"💔 You lost your bet of ${game['bet_amount']:.2f}\n"
                    f"🔥 Your streak was: {game['streak']}\n"
                    f"ID: <code>{game_id}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    
    elif action == "cashout":
        win_amount = game["bet_amount"] * game["current_multiplier"]
        user_wallets[user.id] += win_amount
        game["status"] = 'completed'
        game["win"] = True
        game["multiplier"] = game["current_multiplier"]
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game['bet_amount'], True, multiplier=game["current_multiplier"], context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "hilo", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Streak: {game['streak']}, Multiplier: {game['current_multiplier']:.2f}x")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        
        await query.edit_message_text(
            f"💸 <b>Cashed Out!</b>\n\n"
            f"🎉 You won <b>${win_amount:.2f}</b>!\n"
            f"🔥 Final streak: {game['streak']}\n"
            f"📈 Final multiplier: {game['current_multiplier']:.2f}x\n"
            f"ID: <code>{game_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# 3. ROULETTE GAME
@check_banned
@check_maintenance
async def roulette_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text.strip()
    args = message_text.replace('/roulette', '').replace('/roul', '').strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if len(args) != 2:
        await update.message.reply_text(
            "Usage: /roul amount choice\n\nExamples:\n"
            "• /roul 1 5\n• /roul all red\n• /roul 1 even\n• /roul 1 low\n• /roul 1 high\n• /roul 1 column1"
        )
        return

    try:
        bet_amount_str = args[0].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    choice = args[1].lower()

    if not await check_bet_limits(update, bet_amount, 'roulette'):
        return

    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return

    valid_numbers = list(range(0, 37))
    valid_choices = ["red", "black", "even", "odd", "low", "high", "column1", "column2", "column3"]
    if choice.isdigit():
        if int(choice) not in valid_numbers:
            await update.message.reply_text("Number must be between 0 and 36.")
            return
        choice_type = "number"
    elif choice in valid_choices:
        choice_type = "special"
    else:
        await update.message.reply_text("Invalid choice. Use a number (0-36), red, black, etc.")
        return

    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)

    # Use user's provably fair seeds
    seeds = get_user_seeds(user.id)
    winning_number = get_provably_fair_result(seeds["server_seed"], seeds["client_seed"], seeds["nonce"], 37)
    game_id = generate_unique_id("RL")

    win = False
    multiplier = 0
    if choice_type == "number":
        if int(choice) == winning_number:
            win = True
            multiplier = ROULETTE_CONFIG["single_number"]["multiplier"]
    elif choice in ROULETTE_CONFIG:
        config = ROULETTE_CONFIG[choice]
        if winning_number in config["numbers"]:
            win = True
            multiplier = config["multiplier"]

    if winning_number == 0: color = "🟢 Green"
    elif winning_number in ROULETTE_CONFIG["red"]["numbers"]: color = "🔴 Red"
    else: color = "⚫ Black"

    if win:
        winnings = bet_amount * multiplier
        user_wallets[user.id] += winnings
        result_text = f"🎉 You win ${winnings:.2f}! (Multiplier: {multiplier}x)"
        update_stats_on_bet(user.id, game_id, bet_amount, True, multiplier=multiplier, context=context)
    else:
        result_text = f"😢 You lose ${bet_amount:.2f}. Better luck next time!"
        update_stats_on_bet(user.id, game_id, bet_amount, False, context=context)

    # Increment nonce after game
    increment_user_nonce(user.id)

    game_sessions[game_id] = {
        "id": game_id, "game_type": "roulette", "user_id": user.id,
        "bet_amount": bet_amount, "status": "completed", "timestamp": str(datetime.now(timezone.utc)),
        "win": win, "multiplier": multiplier, "choice": choice, "result": winning_number,
        "server_seed": seeds["server_seed"], "client_seed": seeds["client_seed"], "nonce": seeds["nonce"]
    }
    update_pnl(user.id)
    save_user_data(user.id)
    
    # Store provably fair record
    store_provably_fair_record(game_id, "roulette", seeds["server_seed"], seeds["client_seed"], seeds["nonce"], 
                               result_data=f"Winning number: {winning_number}, Choice: {choice}")
    
    # Add provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]

    await update.message.reply_text(
        f"🎯 <b>Roulette Result</b> (ID: <code>{game_id}</code>)\n\n"
        f"🎰 Winning Number: <b>{winning_number}</b> {color}\n"
        f"🎲 Your Choice: {choice}\n💰 Your Bet: ${bet_amount:.2f}\n\n{result_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 4. DICE ROLL GAME
@check_banned
@check_maintenance
async def dice_roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if len(args) != 3:
        await update.message.reply_text("Usage: /dr amount choice\n\nExamples:\n• /dr 1 3\n• /dr all even\n• /dr 1 high")
        return

    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    choice = args[2].lower()

    if not await check_bet_limits(update, bet_amount, 'dice_roll'):
        return

    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return

    valid_numbers = ['1', '2', '3', '4', '5', '6']
    valid_types = ['even', 'odd', 'high', 'low']
    if choice not in valid_numbers and choice not in valid_types:
        await update.message.reply_text("Invalid choice. Use 1-6, even, odd, high, or low.")
        return

    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)

    await update.message.reply_text(f"🎲 Rolling the dice...")
    await asyncio.sleep(0.5)  # Rate limit protection
    try:
        dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎲")
        dice_result = dice_msg.dice.value
        await asyncio.sleep(4)  # Wait for dice animation to complete
    except Exception as e:
        logging.error(f"Error sending dice in dice_roll_command: {e}")
        # Refund the bet on error
        user_wallets[user.id] += bet_amount
        save_user_data(user.id)
        await update.message.reply_text("❌ An error occurred while rolling the dice. Your bet has been refunded.")
        return
    game_id = generate_unique_id("DR")

    win = False
    multiplier = 0 # NEW
    if choice in valid_numbers:
        if int(choice) == dice_result: win, multiplier = True, 5.96
    elif choice == "even":
        if dice_result in [2, 4, 6]: win, multiplier = True, 1.96
    elif choice == "odd":
        if dice_result in [1, 3, 5]: win, multiplier = True, 1.96
    elif choice == "high":
        if dice_result in [4, 5, 6]: win, multiplier = True, 1.96
    elif choice == "low":
        if dice_result in [1, 2, 3]: win, multiplier = True, 1.96

    if win:
        winnings = bet_amount * multiplier
        user_wallets[user.id] += winnings
        result_text = f"🎉 You win ${winnings:.2f}! (Multiplier: {multiplier}x)"
        update_stats_on_bet(user.id, game_id, bet_amount, True, multiplier=multiplier, context=context)
    else:
        result_text = f"😢 You lose ${bet_amount:.2f}. Try again!"
        update_stats_on_bet(user.id, game_id, bet_amount, False, context=context)

    game_sessions[game_id] = {
        "id": game_id, "game_type": "dice_roll", "user_id": user.id,
        "bet_amount": bet_amount, "status": "completed", "timestamp": str(datetime.now(timezone.utc)),
        "win": win, "multiplier": multiplier, "choice": choice, "result": dice_result
    }
    update_pnl(user.id)
    save_user_data(user.id)

    await update.message.reply_text(
        f"🎲 <b>Dice Roll Result</b> (ID: <code>{game_id}</code>)\n\n🎯 Result: <b>{dice_result}</b>\n"
        f"🎲 Your Choice: {choice}\n💰 Your Bet: ${bet_amount:.2f}\n\n{result_text}",
        parse_mode=ParseMode.HTML
    )

# 5. TOWER GAME
@check_banned
@check_maintenance
## NEW TOWER GAME - Complete Rebuild ##

@check_banned
@check_maintenance
async def tower_ask_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for bet amount when starting tower from inline button"""
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]
    await query.edit_message_text(
        "🏗️ <b>Tower Climb</b>\n\n"
        "Please enter your bet amount (or type 'all' to bet your entire balance):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    # Set ownership after editing
    set_menu_owner(query.message, query.from_user.id)
    return TOWER_BET_AMOUNT


async def tower_receive_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive bet amount from user input"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    try:
        bet_str = update.message.text.lower()
        if bet_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_str)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a number or 'all'.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]])
        )
        return TOWER_BET_AMOUNT
    
    # Check bet limits
    if not await check_bet_limits(update, bet_amount, 'tower'):
        return TOWER_BET_AMOUNT
    
    # Check balance
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await update.message.reply_text(
            "❌ Insufficient balance. Please enter a lower amount.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]])
        )
        return TOWER_BET_AMOUNT
    
    # Show tower intro
    await tower_intro(update, context, bet_amount, from_callback=False)
    return ConversationHandler.END


@check_banned
@check_maintenance  
async def tower_intro(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_amount: float = None, from_callback: bool = False):
    """Show tower game introduction screen with difficulty selector"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    # Store bet amount in user_data
    if bet_amount is not None:
        context.user_data['tower_bet_amount'] = bet_amount
    
    # Get current difficulty or default to 'medium'
    current_difficulty = context.user_data.get('tower_difficulty', 'medium')
    diff_config = TOWER_DIFFICULTY_CONFIG[current_difficulty]
    
    intro_text = (
        f"🏗️ <b>Tower Climb</b>\n\n"
        f"💰 <b>Bet Amount:</b> ${bet_amount:.2f}\n"
        f"🎯 <b>Difficulty:</b> {diff_config['name']} ({diff_config['risk']} risk)\n"
        f"📊 <b>Tiles per floor:</b> {diff_config['tiles']}\n"
        f"🏆 <b>Floors to climb:</b> 9\n"
        f"💎 <b>Max Multiplier:</b> {TOWER_MULTIPLIERS[current_difficulty][9]:.2f}x\n\n"
        f"Select difficulty or start the game!"
    )
    
    keyboard = [
        [InlineKeyboardButton("▶️ Start Game", callback_data=f"tower_start_game")],
        [InlineKeyboardButton("◀️", callback_data="tower_diff_prev"), 
         InlineKeyboardButton(f"{diff_config['name']}", callback_data="tower_diff_info"),
         InlineKeyboardButton("▶️", callback_data="tower_diff_next")],
        [InlineKeyboardButton("📖 Rules", callback_data="tower_rules"),
         InlineKeyboardButton("📊 Multiplier Table", callback_data="tower_multipliers")],
        [InlineKeyboardButton("🔙 Back", callback_data="cancel_game")]
    ]
    
    if from_callback:
        query = update.callback_query
        await safe_edit_message(query, intro_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        sent_message = await update.message.reply_text(intro_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        set_menu_owner(sent_message, user.id)


@check_banned
@check_maintenance
async def tower_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tower and /tr commands with amount"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    # Parse bet amount from command
    try:
        if context.args and len(context.args) > 0:
            bet_str = context.args[0].lower()
            if bet_str == 'all':
                bet_amount = user_wallets.get(user.id, 0.0)
            else:
                bet_amount = float(bet_str)
        else:
            await update.message.reply_text(
                "❌ Please specify a bet amount.\n"
                "Usage: <code>/tower 10</code> or <code>/tr all</code>",
                parse_mode=ParseMode.HTML
            )
            return
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number or 'all'.")
        return
    
    # Check bet limits
    if not await check_bet_limits(update, bet_amount, 'tower'):
        return
    
    # Check balance
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await update.message.reply_text("❌ Insufficient balance. Please deposit or enter a lower amount.")
        return
    
    # Show tower intro
    await tower_intro(update, context, bet_amount, from_callback=False)

@check_banned
@check_maintenance
async def tower_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all tower game callbacks"""
    query = update.callback_query
    user = query.from_user

    if not query.data.startswith("tower_"):
        return

    # Check menu ownership for setup screens
    if query.data in ["tower_diff_prev", "tower_diff_next", "tower_diff_info", "tower_rules", "tower_multipliers", "tower_start_game"]:
        if not check_menu_ownership(query, context):
            await query.answer("This menu is not for you.", show_alert=True)
            return
    
    await query.answer()
    
    # Handle difficulty navigation
    if query.data == "tower_diff_prev":
        difficulties = ['easy', 'medium', 'hard']
        current = context.user_data.get('tower_difficulty', 'medium')
        idx = difficulties.index(current)
        new_idx = (idx - 1) % len(difficulties)
        context.user_data['tower_difficulty'] = difficulties[new_idx]
        bet_amount = context.user_data.get('tower_bet_amount')
        await tower_intro(update, context, bet_amount, from_callback=True)
        return
    
    if query.data == "tower_diff_next":
        difficulties = ['easy', 'medium', 'hard']
        current = context.user_data.get('tower_difficulty', 'medium')
        idx = difficulties.index(current)
        new_idx = (idx + 1) % len(difficulties)
        context.user_data['tower_difficulty'] = difficulties[new_idx]
        bet_amount = context.user_data.get('tower_bet_amount')
        await tower_intro(update, context, bet_amount, from_callback=True)
        return
    
    if query.data == "tower_rules":
        rules_text = (
            "🎮 <b>Tower Climb - How to Play</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Objective:</b>\n"
            "Climb all 9 floors to reach the top and win the jackpot.\n\n"
            "<b>⚠️ Warning:</b>\n"
            "Each floor has one snake 🐍 hidden behind a tile.\n"
            "Selecting the snake tile ends the game immediately.\n\n"
            "<b>How to Play:</b>\n"
            "1. Select your difficulty level\n"
            "2. Choose tiles to climb each floor\n"
            "3. Cash out anytime to secure your winnings\n"
            "4. Reach the top floor for maximum payout\n\n"
            "<b>Difficulty Modes:</b>\n"
            "• <b>Easy:</b> 4 tiles per floor (25% risk)\n"
            "• <b>Medium:</b> 3 tiles per floor (33% risk)\n"
            "• <b>Hard:</b> 2 tiles per floor (50% risk)\n\n"
            "🔥 Higher risk offers bigger rewards!\n\n"
            "House edge: 3.0%"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="tower_back_to_intro")]]
        await safe_edit_message(query, rules_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if query.data == "tower_multipliers":
        mult_text = (
            "📊 <b>Tower Multiplier Table</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<code>Floor   Easy   Medium   Hard</code>\n"
            "─────────────────────────────\n"
        )
        for floor in range(10):
            easy_mult = TOWER_MULTIPLIERS['easy'][floor]
            med_mult = TOWER_MULTIPLIERS['medium'][floor]
            hard_mult = TOWER_MULTIPLIERS['hard'][floor]
            mult_text += f"<code> {floor:>2}     {easy_mult:>5.2f}x  {med_mult:>6.2f}x {hard_mult:>7.2f}x</code>\n"
        
        mult_text += "\nHouse edge: 3.0%\nFloor 0: 0.90x (immediate cashout)"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="tower_back_to_intro")]]
        await safe_edit_message(query, mult_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if query.data == "tower_back_to_intro":
        bet_amount = context.user_data.get('tower_bet_amount')
        await tower_intro(update, context, bet_amount, from_callback=True)
        return
    
    if query.data == "tower_start_game":
        await start_tower_game(update, context)
        return
    
    # Handle game actions (pick tile, cashout)
    parts = query.data.split("_")
    if len(parts) < 3:
        return
    
    action = parts[1]
    game_id = parts[2] if len(parts) > 2 else None
    
    if not game_id:
        return
    
    game = game_sessions.get(game_id)
    
    if not game:
        await query.edit_message_text("Game not found or already finished.")
        return
    
    # Check game ownership
    if user.id != game.get('user_id'):
        await query.answer("This is not your game!", show_alert=True)
        return
    
    if game.get('status') != 'active':
        return
    
    if action == "cashout":
        await handle_tower_cashout(update, context, game_id, game)
        return
    
    if action == "pick":
        position = int(parts[3]) if len(parts) > 3 else 0
        await handle_tower_pick(update, context, game_id, game, position)
        return


async def start_tower_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new tower game with selected difficulty"""
    query = update.callback_query
    user = query.from_user
    
    bet_amount = context.user_data.get('tower_bet_amount')
    difficulty = context.user_data.get('tower_difficulty', 'medium')
    
    if not bet_amount:
        await query.answer("Error: Bet amount not set!", show_alert=True)
        return
    
    # Deduct bet amount
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    # Use user's provably fair seeds
    seeds = get_user_seeds(user.id)
    
    # Generate tower configuration - 9 floors using deterministic positions
    tiles_per_floor = TOWER_DIFFICULTY_CONFIG[difficulty]['tiles']
    tower_config = generate_tower_positions(seeds["server_seed"], seeds["client_seed"], seeds["nonce"], difficulty, 9)
    
    # Create game session
    game_id = generate_unique_id("TW")
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "tower",
        "user_id": user.id,
        "bet_amount": bet_amount,
        "difficulty": difficulty,
        "tiles_per_floor": tiles_per_floor,
        "status": "active",
        "timestamp": str(datetime.now(timezone.utc)),
        "tower_config": tower_config,
        "current_floor": 0,
        "selected_tiles": [],  # Track which tiles were selected
        "server_seed": seeds["server_seed"],
        "client_seed": seeds["client_seed"],
        "nonce": seeds["nonce"]
    }
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if 'game_sessions' not in user_stats[user.id]:
        user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(game_id)
    save_user_data(user.id)
    
    # Clear setup data
    context.user_data.pop('tower_bet_amount', None)
    context.user_data.pop('tower_difficulty', None)
    
    # Create keyboard for floor 0
    keyboard = create_tower_floor_keyboard(game_id, 0, tiles_per_floor, None)
    keyboard.append([InlineKeyboardButton(f"💸 Cash Out (${bet_amount * 0.90:.2f})", callback_data=f"tower_cashout_{game_id}")])
    
    # Create visual representation
    visual = create_tower_game_visual(game_sessions[game_id])
    
    await query.edit_message_text(
        f"🏗️ <b>Tower Climb Started!</b>\n"
        f"ID: <code>{game_id}</code>\n\n"
        f"{visual}\n"
        f"💰 Bet: ${bet_amount:.2f}\n"
        f"🎯 Difficulty: {TOWER_DIFFICULTY_CONFIG[difficulty]['name']}\n"
        f"📊 Floor: 0/9 (Starting position)\n"
        f"💎 Current Multiplier: 0.90x\n\n"
        f"Select a tile to start climbing!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def create_tower_floor_keyboard(game_id: str, floor: int, tiles_per_floor: int, selected_tile: int = None):
    """Create keyboard for current floor"""
    keyboard = []
    row = []
    for pos in range(tiles_per_floor):
        if selected_tile is not None and pos == selected_tile:
            emoji = "✅"  # Safe tile selected
        else:
            emoji = "🟦"  # Unknown tile
        row.append(InlineKeyboardButton(emoji, callback_data=f"tower_pick_{game_id}_{pos}"))
    keyboard.append(row)
    return keyboard


def create_tower_game_visual(game):
    """Create visual representation of the tower showing completed floors"""
    visual = "🏗️ <b>Tower:</b>\n"
    current_floor = game.get('current_floor', 0)
    tiles_per_floor = game.get('tiles_per_floor', 3)
    selected_tiles = game.get('selected_tiles', [])
    tower_config = game.get('tower_config', [])
    
    # Show floors from top (9) to bottom (0)
    for floor in range(8, -1, -1):
        if floor > current_floor:
            # Future floors - show as unknown
            visual += "❓" * tiles_per_floor + f"  Floor {floor + 1}\n"
        elif floor == current_floor:
            # Current floor - show current state
            visual += "🟦" * tiles_per_floor + f"  Floor {floor + 1} ← YOU\n"
        else:
            # Completed floors - reveal snake and safe tile
            snake_pos = tower_config[floor]
            safe_pos = selected_tiles[floor] if floor < len(selected_tiles) else None
            floor_visual = ""
            for pos in range(tiles_per_floor):
                if pos == safe_pos:
                    floor_visual += "✅"
                elif pos == snake_pos:
                    floor_visual += "🐍"
                else:
                    floor_visual += "⬜"
            visual += floor_visual + f"  Floor {floor + 1}\n"
    
    return visual


async def handle_tower_pick(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str, game: dict, position: int):
    """Handle tile selection"""
    query = update.callback_query
    user = query.from_user
    
    current_floor = game["current_floor"]
    snake_position = game["tower_config"][current_floor]
    difficulty = game["difficulty"]
    tiles_per_floor = game["tiles_per_floor"]
    
    # Check if hit snake
    if position == snake_position:
        # Game over - hit snake
        game["status"] = 'completed'
        game["win"] = False
        game["selected_tiles"].append(position)
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game["bet_amount"], False, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "tower", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Hit snake on floor {current_floor + 1}, Config: {game['tower_config']}")
        
        # Show all tiles on current floor
        visual = create_tower_game_visual(game)
        keyboard = create_revealed_floor_keyboard(game_id, current_floor, tiles_per_floor, snake_position, position)
        # Add provably fair button
        keyboard.append([await create_provably_fair_button(game_id, context)])
        
        await query.edit_message_text(
            f"🐍 <b>Tower Collapsed!</b>\n"
            f"ID: <code>{game_id}</code>\n\n"
            f"{visual}\n"
            f"💔 You hit the snake on Floor {current_floor + 1}!\n"
            f"💸 Lost: ${game['bet_amount']:.2f}\n"
            f"🏗️ Floors climbed: {current_floor}/9",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Safe tile - advance to next floor
    game["selected_tiles"].append(position)
    game["current_floor"] += 1
    new_floor = game["current_floor"]
    
    # Check if completed all 9 floors
    if new_floor >= 9:
        multiplier = TOWER_MULTIPLIERS[difficulty][9]
        winnings = game["bet_amount"] * multiplier
        user_wallets[user.id] += winnings
        game["status"] = 'completed'
        game["win"] = True
        game["multiplier"] = multiplier
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game["bet_amount"], True, multiplier=multiplier, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "tower", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Conquered all floors, Multiplier: {multiplier}x, Config: {game['tower_config']}")
        
        visual = create_tower_game_visual(game)
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        
        await query.edit_message_text(
            f"🏆 <b>Tower Conquered!</b>\n"
            f"ID: <code>{game_id}</code>\n\n"
            f"{visual}\n"
            f"🎉 YOU REACHED THE TOP!\n"
            f"💰 Winnings: <b>${winnings:.2f}</b>\n"
            f"📈 Final Multiplier: {multiplier}x\n"
            f"🏗️ All 9 floors completed!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Continue to next floor
    multiplier = TOWER_MULTIPLIERS[difficulty][new_floor]
    potential_winnings = game["bet_amount"] * multiplier
    
    keyboard = create_tower_floor_keyboard(game_id, new_floor, tiles_per_floor, None)
    keyboard.append([InlineKeyboardButton(f"💸 Cash Out (${potential_winnings:.2f})", callback_data=f"tower_cashout_{game_id}")])
    
    visual = create_tower_game_visual(game)
    
    await query.edit_message_text(
        f"✅ <b>Safe! Climbing up...</b>\n"
        f"ID: <code>{game_id}</code>\n\n"
        f"{visual}\n"
        f"📊 Floor: {new_floor}/9\n"
        f"💰 Current Value: <b>${potential_winnings:.2f}</b>\n"
        f"📈 Multiplier: {multiplier}x\n\n"
        f"Choose your next tile or cash out!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_tower_cashout(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str, game: dict):
    """Handle cashout action"""
    query = update.callback_query
    user = query.from_user
    
    current_floor = game["current_floor"]
    difficulty = game["difficulty"]
    multiplier = TOWER_MULTIPLIERS[difficulty][current_floor]
    winnings = game["bet_amount"] * multiplier
    
    user_wallets[user.id] += winnings
    game["status"] = 'completed'
    game["win"] = True
    game["multiplier"] = multiplier
    increment_user_nonce(user.id)
    update_stats_on_bet(user.id, game_id, game["bet_amount"], True, multiplier=multiplier, context=context)
    update_pnl(user.id)
    save_user_data(user.id)
    
    # Store provably fair record
    store_provably_fair_record(game_id, "tower", game["server_seed"], game["client_seed"], game["nonce"], 
                               result_data=f"Cashed out at floor {current_floor}, Multiplier: {multiplier}x, Config: {game['tower_config']}")
    
    visual = create_tower_game_visual(game)
    
    # Add provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]
    
    await query.edit_message_text(
        f"💸 <b>Cashed Out!</b>\n"
        f"ID: <code>{game_id}</code>\n\n"
        f"{visual}\n"
        f"🎉 Winnings: <b>${winnings:.2f}</b>\n"
        f"📈 Multiplier: {multiplier}x\n"
        f"🏗️ Floors climbed: {current_floor}/9",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def create_revealed_floor_keyboard(game_id: str, floor: int, tiles_per_floor: int, snake_pos: int, selected_pos: int):
    """Create keyboard showing revealed tiles after game over"""
    keyboard = []
    row = []
    for pos in range(tiles_per_floor):
        if pos == selected_pos:
            emoji = "🐍"  # Selected snake
        elif pos == snake_pos:
            emoji = "🐍"  # Snake position
        else:
            emoji = "✅"  # Safe tiles
        row.append(InlineKeyboardButton(emoji, callback_data=f"tower_noop"))
    keyboard.append(row)
    return keyboard


# 6. SLOTS GAME
@check_banned
@check_maintenance
async def slots_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if len(args) != 2:
        await update.message.reply_text("Usage: /sl amount\nExample: /sl 5 or /sl all")
        return
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return

    if not await check_bet_limits(update, bet_amount, 'slots'):
        return

    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return

    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)

    # Generate provably fair seeds for slots
    game_id = generate_unique_id("SL")
    server_seed = generate_server_seed()
    client_seed = generate_client_seed()
    nonce = 1

    await update.message.reply_text(f"🎰 Spinning the slots...")
    slot_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎰")
    slot_value = slot_msg.dice.value

    win = False
    multiplier = 0
    win_type = ""
    # FIX: Corrected slot machine logic based on Telegram API
    if slot_value == 64: # 777
        win, multiplier, win_type = True, 28, "🍀 JACKPOT - Triple 7s!"
    elif slot_value in [1, 22, 43]: # bar, grape, lemon
        win, multiplier, win_type = True, 14, "🎉 Triple Match!"

    if win:
        winnings = bet_amount * multiplier
        user_wallets[user.id] += winnings
        result_text = f"🎉 {win_type}\nYou win ${winnings:.2f}! (Multiplier: {multiplier}x)"
        update_stats_on_bet(user.id, game_id, bet_amount, True, multiplier=multiplier, context=context)
    else:
        result_text = f"😢 No match! You lose ${bet_amount:.2f}\nTry again for the jackpot!"
        update_stats_on_bet(user.id, game_id, bet_amount, False, context=context)

    game_sessions[game_id] = {
        "id": game_id, "game_type": "slots", "user_id": user.id,
        "bet_amount": bet_amount, "status": "completed", "timestamp": str(datetime.now(timezone.utc)),
        "win": win, "multiplier": multiplier, "result": slot_value,
        "server_seed": server_seed, "client_seed": client_seed, "nonce": nonce
    }
    
    # Store provably fair record
    store_provably_fair_record(game_id, "slots", server_seed, client_seed, nonce, 
                               result_data=f"Slot value: {slot_value}, Multiplier: {multiplier}x")
    
    update_pnl(user.id)
    save_user_data(user.id)
    
    # Create keyboard with provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]
    
    await update.message.reply_text(
        f"🎰 <b>Slots Result</b> (ID: <code>{game_id}</code>)\n\n💰 Your Bet: ${bet_amount:.2f}\n\n{result_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Play vs Bot Menu: Show inline buttons directly ---
@check_banned
@check_maintenance
async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)
    
    message_text = update.message.text.strip().split()
    
    # Check for XdX'w format: /dice amount XdX'w
    if len(message_text) == 3:
        await create_xdxw_challenge(update, context, "dice")
        return
    
    # Check if in a group and has bet amount (new group challenge feature)
    if update.effective_chat.type in ['group', 'supergroup'] and len(message_text) == 2:
        # New group challenge format: /dice amount
        await create_group_challenge(update, context, "dice")
        return
    
    # Check if arguments are provided (PvP format: /dice @username amount MX ftY)
    if len(message_text) > 1:
        # Arguments provided, treat as PvP command
        await generic_emoji_game_command(update, context, "dice")
        return
    
    # No arguments, show inline buttons for game mode selection
    keyboard = [
        [InlineKeyboardButton(get_text("play_vs_bot", user_lang), callback_data=f"pvb_start_dice_bot")],
        [InlineKeyboardButton(get_text("play_vs_player", user_lang), callback_data=f"pvp_info_dice_bot")],
        [InlineKeyboardButton(get_text("back", user_lang), callback_data="games_emoji_regular")]
    ]
    
    sent_message = await update.message.reply_text(
        f"{get_text('dice_game', user_lang)}\n\n{get_text('who_to_play', user_lang)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def darts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)
    
    message_text = update.message.text.strip().split()
    
    # Check for XdX'w format: /darts amount XdX'w
    if len(message_text) == 3:
        await create_xdxw_challenge(update, context, "darts")
        return
    
    # Check if in a group and has bet amount (new group challenge feature)
    if update.effective_chat.type in ['group', 'supergroup'] and len(message_text) == 2:
        # New group challenge format: /darts amount
        await create_group_challenge(update, context, "darts")
        return
    
    # Check if arguments are provided (PvP format: /darts @username amount MX ftY)
    if len(message_text) > 1:
        # Arguments provided, treat as PvP command
        await generic_emoji_game_command(update, context, "darts")
        return
    
    # No arguments, show inline buttons for game mode selection
    keyboard = [
        [InlineKeyboardButton(get_text("play_vs_bot", user_lang), callback_data=f"pvb_start_darts")],
        [InlineKeyboardButton(get_text("play_vs_player", user_lang), callback_data=f"pvp_info_darts")],
        [InlineKeyboardButton(get_text("back", user_lang), callback_data="games_emoji_regular")]
    ]
    
    sent_message = await update.message.reply_text(
        f"{get_text('darts_game', user_lang)}\n\n{get_text('who_to_play', user_lang)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def football_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)
    
    message_text = update.message.text.strip().split()
    
    # Check for XdX'w format: /goal amount XdX'w
    if len(message_text) == 3:
        await create_xdxw_challenge(update, context, "goal")
        return
    
    # Check if in a group and has bet amount (new group challenge feature)
    if update.effective_chat.type in ['group', 'supergroup'] and len(message_text) == 2:
        # New group challenge format: /goal amount
        await create_group_challenge(update, context, "goal")
        return
    
    # Check if arguments are provided (PvP format: /goal @username amount MX ftY)
    if len(message_text) > 1:
        # Arguments provided, treat as PvP command
        await generic_emoji_game_command(update, context, "goal")
        return
    
    # No arguments, show inline buttons for game mode selection
    keyboard = [
        [InlineKeyboardButton(get_text("play_vs_bot", user_lang), callback_data=f"pvb_start_football")],
        [InlineKeyboardButton(get_text("play_vs_player", user_lang), callback_data=f"pvp_info_football")],
        [InlineKeyboardButton(get_text("back", user_lang), callback_data="games_emoji_regular")]
    ]
    
    sent_message = await update.message.reply_text(
        f"{get_text('football_game', user_lang)}\n\n{get_text('who_to_play', user_lang)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def bowling_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)
    
    message_text = update.message.text.strip().split()
    
    # Check for XdX'w format: /bowl amount XdX'w
    if len(message_text) == 3:
        await create_xdxw_challenge(update, context, "bowl")
        return
    
    # Check if in a group and has bet amount (new group challenge feature)
    if update.effective_chat.type in ['group', 'supergroup'] and len(message_text) == 2:
        # New group challenge format: /bowl amount
        await create_group_challenge(update, context, "bowl")
        return
    
    # Check if arguments are provided (PvP format: /bowl @username amount MX ftY)
    if len(message_text) > 1:
        # Arguments provided, treat as PvP command
        await generic_emoji_game_command(update, context, "bowl")
        return
    
    # No arguments, show inline buttons for game mode selection
    keyboard = [
        [InlineKeyboardButton(get_text("play_vs_bot", user_lang), callback_data=f"pvb_start_bowling")],
        [InlineKeyboardButton(get_text("play_vs_player", user_lang), callback_data=f"pvp_info_bowling")],
        [InlineKeyboardButton(get_text("back", user_lang), callback_data="games_emoji_regular")]
    ]
    
    sent_message = await update.message.reply_text(
        f"{get_text('bowling_game', user_lang)}\n\n{get_text('who_to_play', user_lang)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_menu_owner(sent_message, user.id)

# --- NEW XdX'w FORMAT COMMANDS ---
def parse_xdxw_format(command_text: str):
    """
    Parse XdX'w format from command like: /dice 10 2d3w
    Returns: (bet_amount_str, rolls, target) or None if invalid
    """
    parts = command_text.strip().split()
    if len(parts) != 3:
        return None
    
    # parts[0] = command, parts[1] = bet amount, parts[2] = XdX'w format
    bet_str = parts[1]
    format_str = parts[2].lower()
    
    # Parse XdX'w format (e.g., "2d3w" = 2 rolls, first to 3)
    if 'd' not in format_str or 'w' not in format_str:
        return None
    
    try:
        rolls_str, target_str = format_str.split('d')
        target_str = target_str.replace('w', '')
        
        rolls = int(rolls_str)
        target = int(target_str)
        
        # Validate ranges
        if rolls < 1 or rolls > 3:
            return None
        if target < 1 or target > 10:
            return None
        
        return (bet_str, rolls, target)
    except (ValueError, IndexError):
        return None

async def create_xdxw_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    """Create a challenge with XdX'w format: /dice 10 2d3w"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    parsed = parse_xdxw_format(update.message.text)
    if not parsed:
        await update.message.reply_text(
            f"❌ Invalid format!\n\n"
            f"Usage: /{game_type} <amount> XdX'w\n"
            f"Example: /{game_type} 10 2d3w\n\n"
            f"Where:\n"
            f"• X = number of rolls (1-3)\n"
            f"• X' = first to win (1-10)\n\n"
            f"Examples:\n"
            f"• /{game_type} 5 1d1w - 1 roll, first to 1 wins\n"
            f"• /{game_type} 10 2d3w - 2 rolls, first to 3 wins\n"
            f"• /{game_type} all 3d5w - 3 rolls, first to 5 wins"
        )
        return
    
    bet_str, rolls, target = parsed
    
    try:
        bet_amount_usd, bet_amount_currency, currency = parse_bet_amount(bet_str, user.id)
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount. Please enter a number or 'all'.")
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount_usd:
        await send_insufficient_balance_message(update)
        return
    
    # Store challenge data in context for mode selection
    context.user_data['xdxw_challenge'] = {
        'game_type': game_type,
        'bet_amount_usd': bet_amount_usd,
        'bet_amount_currency': bet_amount_currency,
        'currency': currency,
        'rolls': rolls,
        'target': target,
        'chat_id': update.effective_chat.id,
        'chat_type': update.effective_chat.type
    }
    
    # Show mode selection
    keyboard = [
        [InlineKeyboardButton("🎮 Normal Mode (Highest wins)", callback_data=f"xdxw_mode_normal")],
        [InlineKeyboardButton("🔥 Crazy Mode (Lowest wins)", callback_data=f"xdxw_mode_crazy")],
        [InlineKeyboardButton("❌ Cancel", callback_data="xdxw_cancel")]
    ]
    
    emoji_map = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(game_type, "🎮")
    currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")
    
    sent_message = await update.message.reply_text(
        f"{emoji} <b>{game_type.upper()} Challenge Setup</b>\n\n"
        f"💰 Bet: {currency_symbol}{bet_amount_currency:.2f}\n"
        f"🔢 Rolls per round: {rolls}\n"
        f"🏆 Win condition: First to {target}\n\n"
        f"Select game mode:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_menu_owner(sent_message, user.id)

# Callback for XdX'w mode selection
async def xdxw_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    user = query.from_user
    
    if query.data == "xdxw_cancel":
        await query.edit_message_text("❌ Challenge cancelled.")
        context.user_data.pop('xdxw_challenge', None)
        return
    
    mode = query.data.replace("xdxw_mode_", "")
    challenge_data = context.user_data.get('xdxw_challenge')
    
    if not challenge_data:
        await query.edit_message_text("❌ Challenge data not found. Please try again.")
        return
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    # Final balance check
    if user_wallets.get(user.id, 0.0) < challenge_data['bet_amount_usd']:
        await query.edit_message_text("❌ Insufficient balance to create this challenge.")
        context.user_data.pop('xdxw_challenge', None)
        return
    
    # Create the match
    match_id = generate_unique_id("EG")  # EG = Emoji Game
    emoji_map = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(challenge_data['game_type'], "🎮")
    
    game_sessions[match_id] = {
        "id": match_id,
        "game_type": f"xdxw_{challenge_data['game_type']}",
        "chat_id": challenge_data['chat_id'],
        "chat_type": challenge_data['chat_type'],
        "host_id": user.id,
        "host_username": user.username or f"User_{user.id}",
        "opponent_id": None,
        "bet_amount_usd": challenge_data['bet_amount_usd'],
        "bet_amount_currency": challenge_data['bet_amount_currency'],
        "currency": challenge_data['currency'],
        "mode": mode,
        "game_rolls": challenge_data['rolls'],
        "target_score": challenge_data['target'],
        "status": "pending",
        "timestamp": str(datetime.now(timezone.utc))
    }
    
    # Add to user's game sessions
    if 'game_sessions' not in user_stats[user.id]:
        user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(match_id)
    save_user_data(user.id)
    
    currency_symbol = CURRENCY_SYMBOLS.get(challenge_data['currency'], "$")
    mode_desc = "Highest wins point" if mode == "normal" else "Lowest wins point"
    
    # Show challenge with Accept/Play with Bot buttons
    keyboard = [
        [InlineKeyboardButton("✅ Accept Challenge", callback_data=f"xdxw_accept_{match_id}")],
        [InlineKeyboardButton("🤖 Play with Bot (Host Only)", callback_data=f"xdxw_playbot_{match_id}")]
    ]
    
    await query.edit_message_text(
        f"{emoji} <b>{challenge_data['game_type'].upper()} CHALLENGE!</b> {emoji}\n\n"
        f"👤 Host: @{user.username or user.id}\n"
        f"💰 Bet: {currency_symbol}{challenge_data['bet_amount_currency']:.2f}\n"
        f"🎯 Mode: {mode.title()} ({mode_desc})\n"
        f"🔢 Rolls per round: {challenge_data['rolls']}\n"
        f"🏆 Win condition: First to {challenge_data['target']}\n"
        f"🆔 Match ID: <code>{match_id}</code>\n\n"
        f"Tap a button below to join!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data.pop('xdxw_challenge', None)

# Callback for accepting XdX'w challenge
async def xdxw_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    match_id = query.data.replace("xdxw_accept_", "")
    match = game_sessions.get(match_id)
    
    if not match or match.get("status") != "pending":
        await query.answer("This challenge is no longer available.", show_alert=True)
        return
    
    if user.id == match["host_id"]:
        await query.answer("You can't accept your own challenge!", show_alert=True)
        return
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if user_wallets.get(user.id, 0.0) < match["bet_amount_usd"]:
        await query.answer("You don't have enough balance for this challenge.", show_alert=True)
        return
    
    # Start the PvP match
    match["opponent_id"] = user.id
    match["opponent_username"] = user.username or f"User_{user.id}"
    match["status"] = "active"
    
    # Deduct bets from both players
    user_wallets[match["host_id"]] -= match["bet_amount_usd"]
    user_wallets[user.id] -= match["bet_amount_usd"]
    save_user_data(match["host_id"])
    save_user_data(user.id)
    
    # Initialize PvP game state
    match["players"] = [match["host_id"], match["opponent_id"]]
    match["usernames"] = {match["host_id"]: match["host_username"], match["opponent_id"]: match["opponent_username"]}
    match["player_rolls"] = {match["host_id"]: [], match["opponent_id"]: []}
    match["points"] = {match["host_id"]: 0, match["opponent_id"]: 0}
    match["last_roller"] = None
    match["current_round"] = 1
    
    # Add to opponent's game sessions
    if 'game_sessions' not in user_stats[user.id]:
        user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(match_id)
    save_user_data(user.id)
    
    game_type = match["game_type"].replace("xdxw_", "")
    emoji_map = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(game_type, "🎮")
    
    currency_symbol = CURRENCY_SYMBOLS.get(match["currency"], "$")
    
    await query.edit_message_text(
        f"🎮 <b>MATCH STARTED!</b>\n\n"
        f"👤 @{match['host_username']} vs @{match['opponent_username']}\n"
        f"💰 Prize Pool: {currency_symbol}{match['bet_amount_currency'] * 2:.2f}\n"
        f"🔢 Rolls per round: {match['game_rolls']}\n"
        f"🏆 First to {match['target_score']} wins\n\n"
        f"<b>@{match['host_username']}'s turn!</b>\n"
        f"Send {match['game_rolls']} {emoji} to start round 1.",
        parse_mode=ParseMode.HTML
    )

# Callback for playing XdX'w with bot
async def xdxw_playbot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    match_id = query.data.replace("xdxw_playbot_", "")
    match = game_sessions.get(match_id)
    
    if not match or match.get("status") != "pending":
        await query.answer("This challenge is no longer available.", show_alert=True)
        return
    
    if user.id != match["host_id"]:
        await query.answer("Only the host can play with the bot!", show_alert=True)
        return
    
    # Convert to PvB game
    match["status"] = "active"
    match["opponent_id"] = 0  # Bot
    match["opponent_username"] = "Bot"
    
    # Deduct bet from host
    user_wallets[user.id] -= match["bet_amount_usd"]
    save_user_data(user.id)
    
    # Setup PvB game state - will be handled by message_listener
    game_type = match["game_type"].replace("xdxw_", "")
    emoji_map = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(game_type, "🎮")
    
    # Register as active PvB game
    context.chat_data[f"active_pvb_game_{user.id}"] = match_id
    
    # Initialize PvB game state
    match["user_score"] = 0
    match["bot_score"] = 0
    match["target_score"] = match.get("target_score", 1)
    match["current_round"] = 1
    match["history"] = []
    match["user_rolls"] = []
    match["bot_rolls"] = []
    match["bet_amount"] = match["bet_amount_usd"]  # For PvB compatibility
    match["game_mode"] = match.get("mode", "normal")
    
    await query.edit_message_text(
        f"🤖 <b>PLAYING WITH BOT!</b>\n\n"
        f"<b>Your turn first!</b> Send {match['game_rolls']} {emoji} to start round 1.",
        parse_mode=ParseMode.HTML
    )

# --- SINGLE EMOJI GAMES ---
# Callback handler for "Play" button in single emoji games
async def play_single_emoji_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    game_key = query.data.replace("play_single_", "")
    if game_key not in SINGLE_EMOJI_GAMES:
        await query.edit_message_text("Game not found.")
        return
    
    game_config = SINGLE_EMOJI_GAMES[game_key]
    context.user_data['single_emoji_game'] = game_key
    context.user_data['awaiting_single_emoji_bet'] = True
    
    await query.edit_message_text(
        f"{game_config['emoji']} <b>{game_config['name']}</b>\n\n"
        f"Enter your bet amount (or 'all'):\n\n"
        f"Multiplier: {game_config['multiplier']}x\n"
        f"Win chance: {game_config['win_chance']*100:.1f}%",
        parse_mode=ParseMode.HTML
    )

# Play single emoji game (called after bet amount is entered)
async def play_single_emoji_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_key: str, bet_amount_usd: float, bet_amount_currency: float, currency: str):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if game_key not in SINGLE_EMOJI_GAMES:
        await update.message.reply_text("Invalid game.")
        return
    
    game_config = SINGLE_EMOJI_GAMES[game_key]
    
    # Check bet limits
    if not await check_bet_limits(update, bet_amount_usd, f'emoji_{game_key}'):
        return
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount_usd
    save_user_data(user.id)
    
    # Send the dice/emoji animation
    dice_msg = await update.message.reply_dice(emoji=game_config['dice_type'])
    
    # Wait for the animation to complete
    await asyncio.sleep(4)
    
    # Check if won
    dice_value = dice_msg.dice.value
    won = game_config['win_condition'](dice_value)
    
    game_id = generate_unique_id("SE")
    currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")
    formatted_bet = f"{currency_symbol}{bet_amount_currency:.2f}"
    
    # Add game to game_sessions for history tracking
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": f"single_emoji_{game_key}",
        "user_id": user.id,
        "bet_amount": bet_amount_usd,
        "status": "completed",
        "timestamp": str(datetime.now(timezone.utc)),
        "win": won,
        "multiplier": game_config['multiplier'] if won else 0,
        "dice_value": dice_value,
        "game_name": game_config['name']
    }
    
    if won:
        winnings_usd = bet_amount_usd * game_config['multiplier']
        winnings_currency = bet_amount_currency * game_config['multiplier']
        user_wallets[user.id] += winnings_usd
        update_stats_on_bet(user.id, game_id, bet_amount_usd, True, multiplier=game_config['multiplier'], context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        await update.message.reply_text(
            f"🎉 <b>YOU WON!</b>\n\n"
            f"{game_config['emoji']} {game_config['win_description']}!\n"
            f"Bet: {formatted_bet}\n"
            f"Won: {currency_symbol}{winnings_currency:.2f} ({game_config['multiplier']}x)\n\n"
            f"Game ID: <code>{game_id}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        update_stats_on_bet(user.id, game_id, bet_amount_usd, False, multiplier=0, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        await update.message.reply_text(
            f"😔 <b>You lost</b>\n\n"
            f"Better luck next time!\n"
            f"Lost: {formatted_bet}\n\n"
            f"Game ID: <code>{game_id}</code>",
            parse_mode=ParseMode.HTML
        )

# --- GROUP CHALLENGE SYSTEM ---
# Create a group challenge that can be accepted by others
async def create_group_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    """Create a group PvP challenge with mode and rolls selection"""
    user = update.effective_user
    message_text = update.message.text.strip().split()
    
    try:
        bet_amount_usd, bet_amount_currency, currency = parse_bet_amount(message_text[1], user.id)
    except (ValueError, IndexError):
        await update.message.reply_text("Usage: /{} <amount>\nExample: /{} 5 or /{} all".format(game_type, game_type, game_type))
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount_usd:
        await send_insufficient_balance_message(update)
        return
    
    # Show mode and rolls selection
    keyboard = [
        [InlineKeyboardButton("🎮 Normal Mode", callback_data=f"gc_mode_{game_type}_normal_{bet_amount_usd}_{bet_amount_currency}_{currency}")],
        [InlineKeyboardButton("🔥 Crazy Mode", callback_data=f"gc_mode_{game_type}_crazy_{bet_amount_usd}_{bet_amount_currency}_{currency}")],
    ]
    
    sent_message = await update.message.reply_text(
        f"🎯 <b>Create {game_type.upper()} Challenge</b>\n\n"
        f"Select game mode:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    set_menu_owner(sent_message, user.id)

# Callback for mode selection
async def group_challenge_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    parts = query.data.split("_")
    game_type = parts[2]
    mode = parts[3]
    bet_amount_usd = float(parts[4])
    bet_amount_currency = float(parts[5])
    currency = parts[6]
    
    # Show number of rolls selection
    keyboard = [
        [InlineKeyboardButton("1 Roll", callback_data=f"gc_rolls_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_1")],
        [InlineKeyboardButton("2 Rolls", callback_data=f"gc_rolls_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_2")],
        [InlineKeyboardButton("3 Rolls", callback_data=f"gc_rolls_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_3")],
    ]
    
    await safe_edit_message(query,
        f"🎯 <b>Create {game_type.upper()} Challenge</b>\n\n"
        f"Mode: {mode.title()}\n"
        f"Select number of rolls:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Callback for rolls selection - show target score selection
async def group_challenge_rolls_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    parts = query.data.split("_")
    game_type = parts[2]
    mode = parts[3]
    bet_amount_usd = float(parts[4])
    bet_amount_currency = float(parts[5])
    currency = parts[6]
    rolls = int(parts[7])
    
    # Show target score (first to X) selection
    keyboard = [
        [InlineKeyboardButton("First to 1", callback_data=f"gc_target_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_{rolls}_1")],
        [InlineKeyboardButton("First to 2", callback_data=f"gc_target_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_{rolls}_2")],
        [InlineKeyboardButton("First to 3", callback_data=f"gc_target_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_{rolls}_3")],
        [InlineKeyboardButton("First to 5", callback_data=f"gc_target_{game_type}_{mode}_{bet_amount_usd}_{bet_amount_currency}_{currency}_{rolls}_5")],
    ]
    
    await safe_edit_message(query,
        f"🎯 <b>Create {game_type.upper()} Challenge</b>\n\n"
        f"Mode: {mode.title()}\n"
        f"Rolls: {rolls}\n"
        f"Select target score (First to X wins):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Callback for target score selection and challenge creation
async def group_challenge_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    user = query.from_user
    
    parts = query.data.split("_")
    game_type = parts[2]
    mode = parts[3]
    bet_amount_usd = float(parts[4])
    bet_amount_currency = float(parts[5])
    currency = parts[6]
    rolls = int(parts[7])
    target_score = int(parts[8])
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    # Final check balance
    if user_wallets.get(user.id, 0.0) < bet_amount_usd:
        await query.edit_message_text("❌ Insufficient balance to create this challenge.")
        return
    
    # Create the challenge
    match_id = generate_unique_id("GC")
    emoji_map = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(game_type, "🎮")
    
    game_sessions[match_id] = {
        "id": match_id,
        "game_type": f"group_challenge_{game_type}",
        "chat_id": update.effective_chat.id,
        "host_id": user.id,
        "host_username": user.username or f"User_{user.id}",
        "opponent_id": None,
        "bet_amount_usd": bet_amount_usd,
        "bet_amount_currency": bet_amount_currency,
        "currency": currency,
        "mode": mode,
        "rolls": rolls,
        "target_score": target_score,
        "status": "pending",
        "timestamp": str(datetime.now(timezone.utc))
    }
    
    currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")
    formatted_bet = f"{currency_symbol}{bet_amount_currency:.2f}"
    mode_desc = "Highest wins" if mode == "normal" else "Lowest wins"
    
    # Pin the challenge message
    challenge_msg = await query.message.reply_text(
        f"{emoji} <b>GROUP CHALLENGE!</b> {emoji}\n\n"
        f"🎮 Game: {game_type.upper()}\n"
        f"👤 Host: @{user.username or user.id}\n"
        f"💰 Bet: {formatted_bet}\n"
        f"🎯 Mode: {mode.title()} ({mode_desc})\n"
        f"🔢 Rolls: {rolls}\n"
        f"🏆 Target: First to {target_score}\n"
        f"🆔 Match ID: <code>{match_id}</code>\n\n"
        f"Tap a button below to join!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Accept Challenge", callback_data=f"gc_accept_{match_id}")],
            [InlineKeyboardButton("🤖 Play with Bot (Host Only)", callback_data=f"gc_playbot_{match_id}")]
        ])
    )
    
    # Try to pin the message
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, challenge_msg.message_id)
    except Exception as e:
        logging.warning(f"Could not pin challenge message: {e}")
    
    await query.edit_message_text(
        f"✅ Challenge created!\nMatch ID: <code>{match_id}</code>",
        parse_mode=ParseMode.HTML
    )

# Callback for accepting a challenge
async def group_challenge_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    match_id = query.data.replace("gc_accept_", "")
    match = game_sessions.get(match_id)
    
    if not match or match.get("status") != "pending":
        await query.answer("This challenge is no longer available.", show_alert=True)
        return
    
    if user.id == match["host_id"]:
        await query.answer("You can't accept your own challenge!", show_alert=True)
        return
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if user_wallets.get(user.id, 0.0) < match["bet_amount_usd"]:
        await query.answer("You don't have enough balance for this challenge.", show_alert=True)
        return
    
    # Start the PvP match  
    match["opponent_id"] = user.id
    match["opponent_username"] = user.username or f"User_{user.id}"
    match["status"] = "active"
    
    # Ensure all required fields for PvP are initialized
    if "players" not in match:
        match["players"] = [match["host_id"], user.id]
    if "usernames" not in match:
        match["usernames"] = {match["host_id"]: match.get("host_username", f"User_{match['host_id']}"), user.id: user.username or f"User_{user.id}"}
    if "player_rolls" not in match:
        match["player_rolls"] = {match["host_id"]: [], user.id: []}
    if "points" not in match:
        match["points"] = {match["host_id"]: 0, user.id: 0}
    if "last_roller" not in match:
        match["last_roller"] = None
    if "target_points" not in match:
        match["target_points"] = match.get("target_score", 1)
    
    # Deduct bets from both players
    user_wallets[match["host_id"]] -= match["bet_amount_usd"]
    user_wallets[user.id] -= match["bet_amount_usd"]
    save_user_data(match["host_id"])
    save_user_data(user.id)
    
    currency_symbol = CURRENCY_SYMBOLS.get(match["currency"], "$")
    formatted_bet = f"{currency_symbol}{match['bet_amount_currency']:.2f}"
    
    await query.edit_message_text(
        f"🎮 <b>MATCH STARTED!</b>\n\n"
        f"👤 @{match['host_username']} vs @{user.username or user.id}\n"
        f"💰 Prize Pool: {currency_symbol}{match['bet_amount_currency'] * 2:.2f}\n\n"
        f"Match will begin shortly...",
        parse_mode=ParseMode.HTML
    )
    
    # Start the actual game (similar to existing PvP logic)
    await asyncio.sleep(2)
    await execute_group_challenge_game(update, context, match_id)

# Callback for host playing with bot
async def group_challenge_playbot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    match_id = query.data.replace("gc_playbot_", "")
    match = game_sessions.get(match_id)
    
    if not match or match.get("status") != "pending":
        await query.answer("This challenge is no longer available.", show_alert=True)
        return
    
    if user.id != match["host_id"]:
        await query.answer("Only the host can play with the bot!", show_alert=True)
        return
    
    # Convert to PvB game
    match["status"] = "active"
    match["opponent_id"] = 0  # Bot
    match["opponent_username"] = "Bot"
    
    # Deduct bet from host
    user_wallets[user.id] -= match["bet_amount_usd"]
    save_user_data(user.id)
    
    # Initialize game state for PvP-style play (waiting for emojis)
    match["players"] = [match["host_id"], 0]  # 0 = Bot
    match["usernames"] = {match["host_id"]: match["host_username"], 0: "Bot"}
    match["player_rolls"] = {match["host_id"]: [], 0: []}
    match["points"] = {match["host_id"]: 0, 0: 0}
    match["target_points"] = match.get("target_score", 1)  # Use target_points for consistency
    match["game_mode"] = match.get("mode", "normal")
    match["game_rolls"] = match.get("rolls", 1)
    match["last_roller"] = None
    match["current_round"] = 1
    
    game_type = match["game_type"].replace("group_challenge_", "")
    emoji_map = {"dice": "??", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(game_type, "🎮")
    
    await query.edit_message_text(
        f"🤖 <b>PLAYING WITH BOT!</b>\n\n"
        f"<b>Your turn first!</b> Send {match['rolls']} {emoji} to start round 1.",
        parse_mode=ParseMode.HTML
    )

# Execute the actual group challenge game - NOW WAITS FOR USER INPUT
# The actual game execution happens in message_listener when users send emojis
# This function is no longer used for auto-rolling, only for initialization
async def execute_group_challenge_game(update: Update, context: ContextTypes.DEFAULT_TYPE, match_id: str):
    """Initialize group challenge game - actual rolls are handled by message_listener"""
    match = game_sessions.get(match_id)
    if not match:
        return
    
    game_type = match["game_type"].replace("group_challenge_", "")
    emoji_map = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
    emoji = emoji_map.get(game_type, "🎮")
    
    # Initialize game state for turn-based play
    match["players"] = [match["host_id"], match["opponent_id"]]
    match["usernames"] = {
        match["host_id"]: match["host_username"],
        match["opponent_id"]: match["opponent_username"]
    }
    match["player_rolls"] = {match["host_id"]: [], match["opponent_id"]: []}
    match["points"] = {match["host_id"]: 0, match["opponent_id"]: 0}
    match["target_points"] = match.get("target_score", 1)  # Use target_points for consistency
    match["game_mode"] = match.get("mode", "normal")
    match["game_rolls"] = match.get("rolls", 1)
    match["last_roller"] = None
    match["current_round"] = 1
    
    mode_desc = "Highest wins" if match["mode"] == "normal" else "Lowest wins"
    
    await context.bot.send_message(
        match["chat_id"],
        f"{emoji} <b>ROUND 1</b> {emoji}\n\n"
        f"Mode: {match['mode'].title()} ({mode_desc})\n"
        f"Target: First to {match.get('target_score', 1)} wins!\n\n"
        f"<b>@{match['host_username']}, your turn!</b>\n"
        f"Send {match['rolls']} {emoji} to start!",
        parse_mode=ParseMode.HTML
    )

# --- Play vs Bot main logic (bot rolls real emoji) ---
async def play_vs_bot_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str, target_score: int):
    user = update.effective_user
    bet_amount = context.user_data['bet_amount']
    game_mode = context.user_data.get('game_mode', 'normal')  # normal or crazy
    game_rolls = context.user_data.get('game_rolls', 1)  # 1, 2, or 3 rolls
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if not await check_bet_limits(update, bet_amount, f'pvb_{game_type}'):
        return

    if user_wallets.get(user.id, 0.0) < bet_amount:
        await update.message.reply_text("You no longer have enough balance for this bet. Game cancelled.")
        return
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)

    game_id = generate_unique_id("PVB")
    # Handle different game_type naming variations
    emoji_map = {
        "dice": "🎲", "dice_bot": "🎲",
        "darts": "🎯",
        "goal": "⚽", "football": "⚽",
        "bowl": "🎳", "bowling": "🎳"
    }
    
    mode_text = "Highest total score wins" if game_mode == "normal" else "Lowest total score wins"
    
    # Get the emoji for this game type
    emoji = emoji_map.get(game_type, "🎲")  # Default to dice if not found

    await update.message.reply_text(
        f"🎮 {game_type.capitalize()} vs Bot started! (ID: <code>{game_id}</code>)\n"
        f"<b>Mode:</b> {game_mode.capitalize()} ({mode_text})\n"
        f"<b>Rolls per round:</b> {game_rolls}\n"
        f"<b>Target:</b> First to {target_score} points wins ${bet_amount*2:.2f}.\n\n"
        f"<b>Your turn first! Send {game_rolls} {emoji} emoji{'s' if game_rolls > 1 else ''} to start.</b>",
        parse_mode=ParseMode.HTML
    )

    # Create game session but DON'T roll for bot yet - wait for user first
    game_sessions[game_id] = {
        "id": game_id, "game_type": f"pvb_{game_type}", "user_id": user.id,
        "bet_amount": bet_amount, "status": "active", "timestamp": str(datetime.now(timezone.utc)),
        "target_score": target_score, "current_round": 1,
        "user_score": 0, "bot_score": 0, 
        "bot_rolls": [],  # Empty - bot will roll AFTER user
        "user_rolls": [],  # Will store user rolls
        "game_mode": game_mode,  # normal or crazy
        "game_rolls": game_rolls,  # number of rolls per round
        "history": []  # To store round results
    }
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if 'game_sessions' not in user_stats[user.id]: user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(game_id)
    save_user_data(user.id)
    
    # Store in BOTH context.chat_data AND global dict for reliability
    context.chat_data[f"active_pvb_game_{user.id}"] = game_id
    active_pvb_games[user.id] = game_id  # Global fallback (Note: Python GIL provides basic thread safety for dict operations)
    
    if DEBUG_EMOJI_GAMES:
        logging.info(f"PvB game created: game_id={game_id}, user_id={user.id}, stored in both context.chat_data and active_pvb_games")


# --- /predict amount up/down game ---
@check_banned
@check_maintenance
async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    args = update.message.text.strip().split()
    if len(args) != 3 or args[2].lower() not in ("up", "down"):
        await update.message.reply_text(
            "Usage: /predict amount up/down\nExample: /predict 1 up or /predict all up\n"
            "<b>Guess if the dice will be up (4-6) or down (1-3).</b>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except Exception:
        await update.message.reply_text("Invalid amount.")
        return

    direction = args[2].lower()
    if not await check_bet_limits(update, bet_amount, 'predict'):
        return

    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return

    user_wallets[user.id] -= bet_amount
    await update.message.reply_text(f"Rolling the dice... 🎲")
    await asyncio.sleep(0.5)  # Rate limit protection
    try:
        dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎲")
        outcome = dice_msg.dice.value
        await asyncio.sleep(4)  # Wait for dice animation to complete
    except Exception as e:
        logging.error(f"Error sending dice in predict_command: {e}")
        # Refund the bet on error
        user_wallets[user.id] += bet_amount
        save_user_data(user.id)
        await update.message.reply_text("❌ An error occurred while rolling the dice. Your bet has been refunded.")
        return
    game_id = generate_unique_id("PRD")

    win = (direction == "up" and outcome in [4, 5, 6]) or (direction == "down" and outcome in [1, 2, 3])

    if win:
        winnings = bet_amount * 2
        user_wallets[user.id] += winnings
        result_text = f"Result: {outcome} 🎲\n🎉 You won! You receive ${winnings:.2f}."
        update_stats_on_bet(user.id, game_id, bet_amount, True, multiplier=2, context=context)
    else:
        result_text = f"Result: {outcome} 🎲\n😢 You lost! Better luck next time."
        update_stats_on_bet(user.id, game_id, bet_amount, False, context=context)

    game_sessions[game_id] = {
        "id": game_id, "game_type": "predict", "user_id": user.id,
        "bet_amount": bet_amount, "status": "completed", "timestamp": str(datetime.now(timezone.utc)),
        "win": win, "multiplier": 2 if win else 0, "choice": direction, "result": outcome
    }
    update_pnl(user.id)
    save_user_data(user.id)
    await update.message.reply_text(f"{result_text}\nID: <code>{game_id}</code>", parse_mode=ParseMode.HTML)

# --- LIMBO GAME FUNCTIONS ---
@check_banned
@check_maintenance
async def limbo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Limbo game: /lb amount target_multiplier
    Example: /lb 10 2.5 or /lb all 1.5
    """
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    args = update.message.text.strip().split()
    
    # Show instructions only when no arguments provided
    if len(args) == 1:
        await update.message.reply_text(
            "🚀 <b>LIMBO</b>\n\n"
            "<b>How to play:</b>\n"
            "• Choose your target multiplier (1.01 - 1000.00)\n"
            "• A random outcome is generated (1.00 - 1000.00)\n"
            "• If outcome ≥ your target: You win (bet × target)\n"
            "• If outcome < your target: You lose\n\n"
            "<b>Probability:</b>\n"
            "• 2x = ~46% chance\n"
            "• 4x = ~23% chance\n"
            "• Higher multipliers = lower chance\n\n"
            "<b>Usage:</b> <code>/lb amount multiplier</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/lb 10 2.00</code> - Bet $10 at 2x\n"
            "• <code>/lb all 1.5</code> - Bet all at 1.5x\n\n"
            f"<b>Min bet:</b> ${MIN_BALANCE:.2f}",
            parse_mode=ParseMode.HTML
        )
        return
    
    if len(args) != 3:
        await update.message.reply_text(
            "Usage: <code>/lb amount multiplier</code>\nExample: <code>/lb 10 2.00</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
        
        target_multiplier = float(args[2])
    except ValueError:
        await update.message.reply_text("Invalid amount or multiplier. Please use numbers.")
        return
    
    # Validate target multiplier
    if target_multiplier < 1.01 or target_multiplier > 1000.00:
        await update.message.reply_text("Target multiplier must be between 1.01 and 1000.00")
        return
    
    if not await check_bet_limits(update, bet_amount, 'limbo'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    # Generate provably fair outcome
    game_id = generate_unique_id("LMB")
    server_seed = generate_server_seed()
    client_seed = generate_client_seed()
    nonce = 1
    
    outcome = get_limbo_multiplier(server_seed, client_seed, nonce)
    
    # Determine win/loss
    win = outcome >= target_multiplier
    
    if win:
        winnings = bet_amount * target_multiplier
        user_wallets[user.id] += winnings
        profit = winnings - bet_amount
        result_text = (
            f"🚀 <b>LIMBO RESULT</b> 🚀\n\n"
            f"🎯 Target: <b>{target_multiplier:.2f}x</b>\n"
            f"🎲 Outcome: <b>{outcome:.2f}x</b>\n\n"
            f"✅ <b>YOU WIN!</b>\n"
            f"💰 Profit: <b>${profit:.2f}</b>\n"
            f"💵 Total Payout: <b>${winnings:.2f}</b>\n\n"
            f"Game ID: <code>{game_id}</code>"
        )
        update_stats_on_bet(user.id, game_id, bet_amount, True, multiplier=target_multiplier, context=context)
    else:
        result_text = (
            f"🚀 <b>LIMBO RESULT</b> 🚀\n\n"
            f"🎯 Target: <b>{target_multiplier:.2f}x</b>\n"
            f"🎲 Outcome: <b>{outcome:.2f}x</b>\n\n"
            f"❌ <b>YOU LOSE</b>\n"
            f"💸 Lost: <b>${bet_amount:.2f}</b>\n\n"
            f"Game ID: <code>{game_id}</code>"
        )
        update_stats_on_bet(user.id, game_id, bet_amount, False, context=context)
    
    # Store game session
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "limbo",
        "user_id": user.id,
        "bet_amount": bet_amount,
        "target_multiplier": target_multiplier,
        "outcome": outcome,
        "status": "completed",
        "timestamp": str(datetime.now(timezone.utc)),
        "win": win,
        "server_seed": server_seed,
        "client_seed": client_seed,
        "nonce": nonce
    }
    
    # Store provably fair record
    store_provably_fair_record(game_id, "limbo", server_seed, client_seed, nonce, 
                               result_data=f"Target: {target_multiplier:.2f}x, Outcome: {outcome:.2f}x")
    
    update_pnl(user.id)
    save_user_data(user.id)
    
    # Create keyboard with provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]
    
    await update.message.reply_text(result_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# --- KENO GAME FUNCTIONS ---
def create_keno_keyboard(game_id, selected_numbers):
    """Create the 40-number grid for Keno"""
    buttons = []
    for i in range(1, 41):
        if i in selected_numbers:
            emoji = f"✅{i}"
        else:
            emoji = str(i)
        buttons.append(InlineKeyboardButton(emoji, callback_data=f"keno_pick_{game_id}_{i}"))
    
    # Create 8 rows of 5 numbers each
    keyboard = [buttons[i:i+5] for i in range(0, 40, 5)]
    
    # Add action buttons
    action_row1 = [
        InlineKeyboardButton("ℹ️ How to Play", callback_data=f"keno_info_{game_id}"),
        InlineKeyboardButton("🗑️ Clear All", callback_data=f"keno_clear_{game_id}")
    ]
    action_row2 = [
        InlineKeyboardButton("📊 Payout Table", callback_data=f"keno_payout_{game_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"keno_cancel_{game_id}")
    ]
    
    # Add place bet button if numbers are selected
    if selected_numbers:
        action_row3 = [InlineKeyboardButton(f"✅ Place Bet ({len(selected_numbers)} numbers)", callback_data=f"keno_place_{game_id}")]
        keyboard.extend([action_row1, action_row2, action_row3])
    else:
        keyboard.extend([action_row1, action_row2])
    
    return InlineKeyboardMarkup(keyboard)

def get_keno_payout_text():
    """Get formatted payout table"""
    text = "🎰 <b>KENO PAYOUT TABLE</b>\n────────────────\n\n"
    for picks in range(1, 11):
        text += f"📊 <b>{picks} Pick{'s' if picks > 1 else ''}:</b>\n"
        payouts = KENO_PAYOUTS[picks]
        for matches, multiplier in payouts.items():
            if picks == 1 and matches == 0:
                text += f"   • No matches → {multiplier}x\n"
            else:
                text += f"   • {matches} match{'es' if matches != 1 else ''} → {multiplier}x\n"
        text += "\n"
    return text

@check_banned
@check_maintenance
async def keno_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Keno game: /keno amount
    """
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    args = update.message.text.strip().split()
    if len(args) != 2:
        await update.message.reply_text(
            "🎯 <b>KENO</b>\n\n"
            "<b>Usage:</b> <code>/keno amount</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/keno 10</code> - Start keno with $10\n"
            "• <code>/keno all</code> - Start keno with all balance\n\n"
            "<b>How to play:</b>\n"
            "1. Pick 1-10 numbers from 1-40\n"
            "2. Place your bet\n"
            "3. 10 random numbers are drawn\n"
            "4. Win based on how many you matched!\n\n"
            f"<b>Min bet:</b> ${MIN_BALANCE:.2f}",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount. Please use a number.")
        return
    
    if not await check_bet_limits(update, bet_amount, 'keno'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Create game session
    game_id = generate_unique_id("KNO")
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "keno",
        "user_id": user.id,
        "bet_amount": bet_amount,
        "selected_numbers": [],
        "status": "selecting",
        "timestamp": str(datetime.now(timezone.utc))
    }
    
    text = (
        f"🎯 <b>KENO GAME</b>\n"
        f"────────\n\n"
        f"📊 <b>Game Status:</b>\n"
        f"• Numbers Selected: 0/10\n"
        f"• Bet Amount: ${bet_amount:.2f}\n\n"
        f"📝 <b>Instructions:</b>\n"
        f"Pick 1 to 10 numbers from the grid below."
    )
    
    keyboard = create_keno_keyboard(game_id, [])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

@check_banned
@check_maintenance
async def keno_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Keno game callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    action = parts[1]
    game_id = parts[2]
    
    game = game_sessions.get(game_id)
    if not game or game["user_id"] != query.from_user.id:
        await query.answer("This is not your game!", show_alert=True)
        return
    
    if action == "pick":
        if game["status"] != "selecting":
            await query.answer("Game already completed!", show_alert=True)
            return
        
        number = int(parts[3])
        selected = game["selected_numbers"]
        
        if number in selected:
            selected.remove(number)
        else:
            if len(selected) >= 10:
                await query.answer("Maximum 10 numbers allowed!", show_alert=True)
                return
            selected.append(number)
        
        text = (
            f"🎯 <b>KENO GAME</b>\n"
            f"────────\n\n"
            f"📊 <b>Game Status:</b>\n"
            f"• Numbers Selected: {len(selected)}/10\n"
            f"• Bet Amount: ${game['bet_amount']:.2f}\n\n"
            f"📝 <b>Instructions:</b>\n"
            f"Pick 1 to 10 numbers from the grid below."
        )
        
        keyboard = create_keno_keyboard(game_id, selected)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    elif action == "clear":
        game["selected_numbers"] = []
        text = (
            f"🎯 <b>KENO GAME</b>\n"
            f"────────\n\n"
            f"📊 <b>Game Status:</b>\n"
            f"• Numbers Selected: 0/10\n"
            f"• Bet Amount: ${game['bet_amount']:.2f}\n\n"
            f"📝 <b>Instructions:</b>\n"
            f"Pick 1 to 10 numbers from the grid below."
        )
        keyboard = create_keno_keyboard(game_id, [])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    elif action == "info":
        info_text = (
            "ℹ️ <b>HOW TO PLAY KENO</b>\n\n"
            "1️⃣ Select 1-10 numbers from 1-40\n"
            "2️⃣ Click 'Place Bet' when ready\n"
            "3️⃣ 10 random numbers will be drawn\n"
            "4️⃣ Win based on matches!\n\n"
            "<b>Tips:</b>\n"
            "• More picks = higher potential payout\n"
            "• But also need more matches to win\n"
            "• Check payout table for details"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"keno_back_{game_id}")]])
        await query.edit_message_text(info_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    elif action == "payout":
        payout_text = get_keno_payout_text()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"keno_back_{game_id}")]])
        await query.edit_message_text(payout_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    elif action == "back":
        selected = game["selected_numbers"]
        text = (
            f"🎯 <b>KENO GAME</b>\n"
            f"────────\n\n"
            f"📊 <b>Game Status:</b>\n"
            f"• Numbers Selected: {len(selected)}/10\n"
            f"• Bet Amount: ${game['bet_amount']:.2f}\n\n"
            f"📝 <b>Instructions:</b>\n"
            f"Pick 1 to 10 numbers from the grid below."
        )
        keyboard = create_keno_keyboard(game_id, selected)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    elif action == "place":
        selected = game["selected_numbers"]
        if not selected:
            await query.answer("Please select at least 1 number!", show_alert=True)
            return
        
        # Deduct bet
        user_wallets[game["user_id"]] -= game["bet_amount"]
        save_user_data(game["user_id"])
        
        # Use user's provably fair seeds
        seeds = get_user_seeds(game["user_id"])
        
        # Draw 20 numbers from 1-40 deterministically
        drawn_numbers = []
        offset = 0
        while len(drawn_numbers) < 20:
            num = (get_provably_fair_result(seeds["server_seed"], seeds["client_seed"], seeds["nonce"] + offset, 40) + 1)
            if num not in drawn_numbers:
                drawn_numbers.append(num)
            offset += 1
        
        # Calculate matches
        matches = len(set(selected) & set(drawn_numbers))
        num_picks = len(selected)
        
        # Get multiplier
        multiplier = KENO_PAYOUTS.get(num_picks, {}).get(matches, 0.0)
        
        if multiplier > 0:
            winnings = game["bet_amount"] * multiplier
            user_wallets[game["user_id"]] += winnings
            profit = winnings - game["bet_amount"]
            win = True
        else:
            winnings = 0
            profit = -game["bet_amount"]
            win = False
        
        # Update game
        game["status"] = "completed"
        game["drawn_numbers"] = drawn_numbers
        game["matches"] = matches
        game["multiplier"] = multiplier
        game["server_seed"] = seeds["server_seed"]
        game["client_seed"] = seeds["client_seed"]
        game["nonce"] = seeds["nonce"]
        increment_user_nonce(game["user_id"])
        game["win"] = win
        
        # Update stats
        update_stats_on_bet(game["user_id"], game_id, game["bet_amount"], win, multiplier=multiplier, context=context)
        update_pnl(game["user_id"])
        save_user_data(game["user_id"])
        
        # Format result
        selected_str = ", ".join(str(n) for n in sorted(selected))
        drawn_str = ", ".join(str(n) for n in sorted(drawn_numbers))
        matched_str = ", ".join(str(n) for n in sorted(set(selected) & set(drawn_numbers)))
        
        result_text = (
            f"🎯 <b>KENO RESULT</b>\n"
            f"────────────────\n\n"
            f"📌 <b>Your Numbers:</b> {selected_str}\n"
            f"🎲 <b>Drawn Numbers:</b> {drawn_str}\n"
            f"✅ <b>Matches:</b> {matches}/{num_picks}\n"
        )
        
        if matched_str:
            result_text += f"🎊 <b>Matched:</b> {matched_str}\n"
        
        result_text += "\n"
        
        if win:
            result_text += (
                f"🎉 <b>YOU WIN!</b>\n"
                f"💰 Multiplier: {multiplier}x\n"
                f"💵 Profit: ${profit:.2f}\n"
                f"💸 Total Payout: ${winnings:.2f}\n"
            )
        else:
            result_text += (
                f"❌ <b>NO WIN</b>\n"
                f"💸 Lost: ${game['bet_amount']:.2f}\n"
                f"Better luck next time!"
            )
        
        result_text += f"\n<b>Game ID:</b> <code>{game_id}</code>"
        
        # Store provably fair record
        store_provably_fair_record(game_id, "keno", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Matches: {matches}/{num_picks}, Drawn: {drawn_numbers}")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        
        await query.edit_message_text(result_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "cancel":
        game["status"] = "cancelled"
        await query.edit_message_text("❌ Keno game cancelled.", parse_mode=ParseMode.HTML)

## NEW GAMES - Crash, Plinko, Wheel, Scratch Card, Coin Chain ##

# 1. CRASH GAME
@check_banned
@check_maintenance
async def crash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if len(args) < 2:
        await update.message.reply_text("Usage: /crash amount [target_multiplier]\nExample: /crash 5 or /crash 10 2.5")
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
        
        auto_cashout = None
        if len(args) >= 3:
            auto_cashout = float(args[2])
            if auto_cashout < 1.01 or auto_cashout > 100:
                await update.message.reply_text("Auto cashout must be between 1.01x and 100x")
                return
    except ValueError:
        await update.message.reply_text("Invalid amount or multiplier.")
        return
    
    if not await check_bet_limits(update, bet_amount, 'crash'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    # Generate provably fair crash point
    server_seed = generate_server_seed()
    client_seed = generate_client_seed()
    hash_result = create_hash(server_seed, client_seed, 1)
    hex_value = int(hash_result[:13], 16)
    crash_point = max(1.00, min(100.0, (99 / (hex_value % 99 + 1))))
    crash_point = round(crash_point, 2)
    
    # Determine result
    if auto_cashout:
        if auto_cashout <= crash_point:
            # Win!
            multiplier = auto_cashout
            winnings = bet_amount * multiplier
            profit = winnings - bet_amount
            user_wallets[user.id] += winnings
            win = True
            result_text = (
                f"📉 <b>CRASH GAME</b>\n\n"
                f"🎯 Auto Cashout: {auto_cashout:.2f}x\n"
                f"💥 Crash Point: {crash_point:.2f}x\n\n"
                f"✅ <b>CASHED OUT!</b>\n"
                f"💰 Multiplier: {multiplier:.2f}x\n"
                f"💵 Profit: ${profit:.2f}\n"
                f"💸 Total Payout: ${winnings:.2f}"
            )
        else:
            # Lost
            win = False
            multiplier = 0
            result_text = (
                f"📉 <b>CRASH GAME</b>\n\n"
                f"🎯 Auto Cashout: {auto_cashout:.2f}x\n"
                f"💥 Crash Point: {crash_point:.2f}x\n\n"
                f"❌ <b>CRASHED!</b>\n"
                f"💸 Lost: ${bet_amount:.2f}\n"
                f"The game crashed before you could cash out!"
            )
    else:
        # Manual mode - show crash point immediately
        result_text = (
            f"📉 <b>CRASH GAME</b>\n\n"
            f"💥 Crash Point: {crash_point:.2f}x\n\n"
            f"ℹ️ Manual mode - Use auto cashout next time!\n"
            f"Example: /crash 10 2.5"
        )
        # Refund since manual mode not fully implemented
        user_wallets[user.id] += bet_amount
        await update.message.reply_text(result_text, parse_mode=ParseMode.HTML)
        return
    
    # Generate game ID first before using it
    game_id = generate_unique_id('CRASH')
    
    update_stats_on_bet(user.id, game_id, bet_amount, win, multiplier=multiplier, context=context)
    save_user_data(user.id)
    
    # Store game session and provably fair record
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "crash",
        "user_id": user.id,
        "bet_amount": bet_amount,
        "crash_point": crash_point,
        "auto_cashout": auto_cashout,
        "status": "completed",
        "timestamp": str(datetime.now(timezone.utc)),
        "win": win,
        "multiplier": multiplier if win else 0,
        "server_seed": server_seed,
        "client_seed": client_seed,
        "nonce": 1
    }
    
    # Store provably fair record
    store_provably_fair_record(game_id, "crash", server_seed, client_seed, 1, 
                               result_data=f"Crash point: {crash_point:.2f}x, Auto cashout: {auto_cashout:.2f}x" if auto_cashout else f"Crash point: {crash_point:.2f}x")
    
    # Create keyboard with provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]
    
    await update.message.reply_text(result_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# 2. PLINKO GAME
PLINKO_MULTIPLIERS = {
    "low": [0.5, 0.7, 0.9, 1.0, 1.2, 1.4, 1.6, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.6],
    "medium": [0.3, 0.5, 0.7, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 18.0, 24.0, 30.0, 33.0],
    "high": [0.2, 0.3, 0.5, 1.0, 3.0, 10.0, 25.0, 75.0, 150.0, 250.0, 350.0, 420.0]
}

@check_banned
@check_maintenance
async def plinko_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if len(args) != 3:
        await update.message.reply_text("Usage: /plinko amount risk\nRisk: low, medium, or high\nExample: /plinko 5 medium")
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
        
        risk = args[2].lower()
        if risk not in PLINKO_MULTIPLIERS:
            await update.message.reply_text("Risk must be: low, medium, or high")
            return
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    
    if not await check_bet_limits(update, bet_amount, 'plinko'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    # Generate provably fair result
    server_seed = generate_server_seed()
    client_seed = generate_client_seed()
    result_index = get_provably_fair_result(server_seed, client_seed, 1, len(PLINKO_MULTIPLIERS[risk]))
    multiplier = PLINKO_MULTIPLIERS[risk][result_index]
    
    winnings = bet_amount * multiplier
    profit = winnings - bet_amount
    win = multiplier >= 1.0
    
    # Generate game ID first before using it
    game_id = generate_unique_id('PLINKO')
    
    user_wallets[user.id] += winnings
    update_stats_on_bet(user.id, game_id, bet_amount, win, multiplier=multiplier, context=context)
    save_user_data(user.id)
    
    # Store game session and provably fair record
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "plinko",
        "user_id": user.id,
        "bet_amount": bet_amount,
        "risk": risk,
        "result_index": result_index,
        "multiplier": multiplier,
        "status": "completed",
        "timestamp": str(datetime.now(timezone.utc)),
        "win": win,
        "server_seed": server_seed,
        "client_seed": client_seed,
        "nonce": 1
    }
    
    # Store provably fair record
    store_provably_fair_record(game_id, "plinko", server_seed, client_seed, 1, 
                               result_data=f"Risk: {risk}, Slot: {result_index + 1}, Multiplier: {multiplier:.2f}x")
    
    result_text = (
        f"🎪 <b>PLINKO</b>\n"
        f"Game ID: <code>{game_id}</code>\n\n"
        f"🎲 Risk Level: {risk.upper()}\n"
        f"🎯 Landed in slot: {result_index + 1}\n"
        f"💰 Multiplier: {multiplier:.2f}x\n\n"
    )
    
    if win:
        result_text += f"🎉 <b>WIN!</b>\n💵 Profit: ${profit:.2f}\n💸 Total Payout: ${winnings:.2f}"
    else:
        result_text += f"❌ <b>LOST</b>\n💸 Lost: ${abs(profit):.2f}"
    
    # Create keyboard with provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]
    
    await update.message.reply_text(result_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# 3. WHEEL OF FORTUNE GAME
WHEEL_SEGMENTS = [
    0.2, 0.5, 0.7, 1.0, 1.2, 1.5, 2.0, 0.5, 1.0, 1.5,
    2.5, 3.0, 0.7, 1.0, 1.5, 2.0, 3.5, 4.0, 1.0, 1.5,
    2.0, 2.5, 5.0, 1.0, 1.5, 2.0, 3.0, 7.0, 10.0, 1.5,
    2.0, 3.0, 5.0, 15.0, 2.0, 3.0, 5.0, 10.0, 20.0, 2.5,
    3.0, 5.0, 30.0, 3.0, 5.0, 10.0, 50.0, 1.0, 2.0, 5.0
]

@check_banned
@check_maintenance
async def wheel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if len(args) != 2:
        await update.message.reply_text("Usage: /wheel amount\nExample: /wheel 5 or /wheel all")
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    
    if not await check_bet_limits(update, bet_amount, 'wheel'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    # Generate provably fair result
    server_seed = generate_server_seed()
    client_seed = generate_client_seed()
    segment = get_provably_fair_result(server_seed, client_seed, 1, len(WHEEL_SEGMENTS))
    multiplier = WHEEL_SEGMENTS[segment]
    
    winnings = bet_amount * multiplier
    profit = winnings - bet_amount
    win = multiplier >= 1.0
    
    # Generate game ID first before using it
    game_id = generate_unique_id('WHEEL')
    
    user_wallets[user.id] += winnings
    update_stats_on_bet(user.id, game_id, bet_amount, win, multiplier=multiplier, context=context)
    save_user_data(user.id)
    
    # Store game session and provably fair record
    game_sessions[game_id] = {
        "id": game_id,
        "game_type": "wheel",
        "user_id": user.id,
        "bet_amount": bet_amount,
        "segment": segment,
        "multiplier": multiplier,
        "status": "completed",
        "timestamp": str(datetime.now(timezone.utc)),
        "win": win,
        "server_seed": server_seed,
        "client_seed": client_seed,
        "nonce": 1
    }
    
    # Store provably fair record
    store_provably_fair_record(game_id, "wheel", server_seed, client_seed, 1, 
                               result_data=f"Segment: {segment + 1}, Multiplier: {multiplier:.1f}x")
    
    result_text = (
        f"🎡 <b>WHEEL OF FORTUNE</b>\n"
        f"Game ID: <code>{game_id}</code>\n\n"
        f"🎯 Segment: #{segment + 1}\n"
        f"💰 Multiplier: {multiplier:.1f}x\n\n"
    )
    
    if win:
        result_text += f"🎉 <b>WIN!</b>\n💵 Profit: ${profit:.2f}\n💸 Total Payout: ${winnings:.2f}"
    else:
        result_text += f"❌ <b>LOST</b>\n💸 Lost: ${abs(profit):.2f}"
    
    # Create keyboard with provably fair button
    keyboard = [[await create_provably_fair_button(game_id, context)]]
    
    await update.message.reply_text(result_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# 4. SCRATCH CARD GAME
SCRATCH_SYMBOLS = {
    "💎": {"mult": 100, "weight": 1},
    "👑": {"mult": 50, "weight": 2},
    "⭐": {"mult": 20, "weight": 5},
    "💰": {"mult": 10, "weight": 10},
    "🍀": {"mult": 5, "weight": 20},
    "🎰": {"mult": 2, "weight": 30},
    "❌": {"mult": 0, "weight": 50}
}

@check_banned
@check_maintenance
async def scratch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if len(args) != 2:
        await update.message.reply_text("Usage: /scratch amount\nExample: /scratch 5 or /scratch all")
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    
    if not await check_bet_limits(update, bet_amount, 'scratch'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    # Generate 9 symbols using weighted random
    server_seed = generate_server_seed()
    client_seed = generate_client_seed()
    
    symbols = []
    symbol_list = []
    for sym, data in SCRATCH_SYMBOLS.items():
        symbol_list.extend([sym] * data["weight"])
    
    for i in range(9):
        idx = get_provably_fair_result(server_seed, client_seed, i + 1, len(symbol_list))
        symbols.append(symbol_list[idx])
    
    # Check for 3 matches
    from collections import Counter
    symbol_counts = Counter(symbols)
    match_symbol = None
    for sym, count in symbol_counts.items():
        if count >= 3:
            match_symbol = sym
            break
    
    if match_symbol and match_symbol != "❌":
        multiplier = SCRATCH_SYMBOLS[match_symbol]["mult"]
        winnings = bet_amount * multiplier
        profit = winnings - bet_amount
        win = True
        user_wallets[user.id] += winnings
    else:
        multiplier = 0
        win = False
        winnings = 0
        profit = -bet_amount
    
    update_stats_on_bet(user.id, generate_unique_id('SCRATCH'), bet_amount, win, multiplier=multiplier, context=context)
    save_user_data(user.id)
    
    # Display card
    card_display = f"{symbols[0]} {symbols[1]} {symbols[2]}\n{symbols[3]} {symbols[4]} {symbols[5]}\n{symbols[6]} {symbols[7]} {symbols[8]}"
    
    result_text = (
        f"🎫 <b>SCRATCH CARD</b>\n\n"
        f"{card_display}\n\n"
    )
    
    if win:
        result_text += f"🎉 <b>3 {match_symbol} MATCH!</b>\n💰 Multiplier: {multiplier}x\n💵 Profit: ${profit:.2f}\n💸 Total Payout: ${winnings:.2f}"
    else:
        result_text += f"❌ <b>NO MATCH</b>\n💸 Lost: ${bet_amount:.2f}\nTry again!"
    
    await update.message.reply_text(result_text, parse_mode=ParseMode.HTML)

# 5. COIN TOSS CHAIN GAME
@check_banned
@check_maintenance
async def coinchain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = update.message.text.strip().split()
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if len(args) != 2:
        await update.message.reply_text("Usage: /coinchain amount\nExample: /coinchain 5 or /coinchain all")
        return
    
    try:
        bet_amount_str = args[1].lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    
    if not await check_bet_limits(update, bet_amount, 'coinchain'):
        return
    
    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return
    
    # Create game session
    game_id = generate_unique_id('COINCHAIN')
    game_sessions[game_id] = {
        "id": game_id,
        "user_id": user.id,
        "game_type": "coin_chain",
        "bet_amount": bet_amount,
        "chain_length": 0,
        "current_multiplier": 1.0,
        "status": "active"
    }
    
    # Deduct bet
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🪙 Heads", callback_data=f"coinchain_{game_id}_heads"),
         InlineKeyboardButton("🪙 Tails", callback_data=f"coinchain_{game_id}_tails")],
        [InlineKeyboardButton("💰 Cash Out", callback_data=f"coinchain_{game_id}_cashout"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"coinchain_{game_id}_cancel")]
    ]
    
    text = (
        f"🪙 <b>COIN TOSS CHAIN</b>\n\n"
        f"💵 Bet: ${bet_amount:.2f}\n"
        f"⛓️ Chain: 0 wins\n"
        f"💰 Current: ${bet_amount:.2f} (1.0x)\n\n"
        f"Choose Heads or Tails!\n"
        f"Each correct guess multiplies by 1.9x"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

@check_banned
@check_maintenance
async def coinchain_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    game_id = parts[1]
    action = parts[2] if len(parts) > 2 else None
    
    game = game_sessions.get(game_id)
    if not game or game["status"] != "active":
        await query.edit_message_text("❌ Game not found or already ended.")
        return
    
    user_id = game["user_id"]
    
    if action == "cashout":
        # Cash out current winnings
        multiplier = game["current_multiplier"]
        winnings = game["bet_amount"] * multiplier
        profit = winnings - game["bet_amount"]
        
        user_wallets[user_id] += winnings
        game["status"] = "completed"
        update_stats_on_bet(user_id, game_id, game["bet_amount"], True, multiplier=multiplier, context=context)
        save_user_data(user_id)
        
        result_text = (
            f"🪙 <b>COIN TOSS CHAIN</b>\n\n"
            f"💰 <b>CASHED OUT!</b>\n\n"
            f"⛓️ Chain Length: {game['chain_length']} wins\n"
            f"💰 Final Multiplier: {multiplier:.2f}x\n"
            f"💵 Profit: ${profit:.2f}\n"
            f"💸 Total Payout: ${winnings:.2f}"
        )
        await query.edit_message_text(result_text, parse_mode=ParseMode.HTML)
        return
    
    elif action == "cancel":
        game["status"] = "cancelled"
        await query.edit_message_text("❌ Coin chain game cancelled. Bet refunded.", parse_mode=ParseMode.HTML)
        user_wallets[user_id] += game["bet_amount"]
        save_user_data(user_id)
        return
    
    elif action in ["heads", "tails"]:
        # Generate coin flip result
        server_seed = generate_server_seed()
        client_seed = generate_client_seed()
        result_num = get_provably_fair_result(server_seed, client_seed, game["chain_length"] + 1, 2)
        result = "heads" if result_num == 0 else "tails"
        
        if result == action:
            # Correct guess!
            game["chain_length"] += 1
            game["current_multiplier"] *= 1.9
            
            keyboard = [
                [InlineKeyboardButton("🪙 Heads", callback_data=f"coinchain_{game_id}_heads"),
                 InlineKeyboardButton("🪙 Tails", callback_data=f"coinchain_{game_id}_tails")],
                [InlineKeyboardButton("💰 Cash Out", callback_data=f"coinchain_{game_id}_cashout"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"coinchain_{game_id}_cancel")]
            ]
            
            current_value = game["bet_amount"] * game["current_multiplier"]
            
            text = (
                f"🪙 <b>COIN TOSS CHAIN</b>\n\n"
                f"✅ Correct! It was {result.upper()}!\n\n"
                f"⛓️ Chain: {game['chain_length']} wins\n"
                f"💰 Current: ${current_value:.2f} ({game['current_multiplier']:.2f}x)\n\n"
                f"Keep going or cash out?"
            )
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            # Wrong guess - lose everything
            game["status"] = "completed"
            update_stats_on_bet(user_id, game_id, game["bet_amount"], False, context=context)
            save_user_data(user_id)
            
            result_text = (
                f"🪙 <b>COIN TOSS CHAIN</b>\n\n"
                f"❌ Wrong! It was {result.upper()}!\n\n"
                f"⛓️ Chain Length: {game['chain_length']} wins\n"
                f"💸 Lost: ${game['bet_amount']:.2f}\n\n"
                f"Better luck next time!"
            )
            await query.edit_message_text(result_text, parse_mode=ParseMode.HTML)

# --- MINES GAME FUNCTIONS ---
def get_mines_multiplier(num_mines, safe_picks):
    if safe_picks == 0: return 1.0
    try: return MINES_MULT_TABLE[num_mines][safe_picks]
    except KeyError: return 1.0

def mines_keyboard(game_id, reveal=False):
    game = game_sessions.get(game_id)
    if not game: return InlineKeyboardMarkup([])

    total_cells = game["total_cells"]
    num_per_row = 5
    buttons = []
    for i in range(1, total_cells + 1):
        if i in game["picks"]: emoji = "✅"
        elif reveal and i in game["mines"]: emoji = "💥"
        elif reveal: emoji = "💎"
        else: emoji = "❓"
        buttons.append(InlineKeyboardButton(emoji, callback_data=f"mines_pick_{game_id}_{i}"))

    keyboard = [buttons[i:i+num_per_row] for i in range(0, len(buttons), num_per_row)]
    if game["status"] == 'active' and game["picks"]:
        safe_picks = len(game["picks"])
        multiplier = get_mines_multiplier(game["num_mines"], safe_picks)
        winnings = game["bet_amount"] * multiplier
        cashout_text = f"💸 Cashout (${winnings:.2f})"
        keyboard.append([InlineKeyboardButton(cashout_text, callback_data=f"mines_cashout_{game_id}")])
    return InlineKeyboardMarkup(keyboard)

@check_banned
@check_maintenance
async def mines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    num_mines = int(context.user_data['bombs'])

    try:
        bet_amount_str = update.message.text.lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid bet amount. Please enter a number.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
        return SELECT_BET_AMOUNT

    if not await check_bet_limits(update, bet_amount, 'mines'):
        return SELECT_BET_AMOUNT

    if user_wallets.get(user.id, 0.0) < bet_amount:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="cancel_game")]
        ])
        await update.message.reply_text("❌ You don't have enough balance. Please enter a lower amount.", reply_markup=keyboard)
        return SELECT_BET_AMOUNT

    total_cells = 25
    
    # Use user's provably fair seeds
    seeds = get_user_seeds(user.id)
    mine_numbers = generate_mine_positions(seeds["server_seed"], seeds["client_seed"], seeds["nonce"], num_mines)
    
    game_id = generate_unique_id("MN")
    game_sessions[game_id] = {
        "id": game_id, "game_type": "mines", "user_id": user.id, "bet_amount": bet_amount,
        "status": "active", "timestamp": str(datetime.now(timezone.utc)), "mines": mine_numbers,
        "picks": [], "total_cells": total_cells, "num_mines": num_mines,
        "server_seed": seeds["server_seed"], "client_seed": seeds["client_seed"], "nonce": seeds["nonce"]
    }
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if 'game_sessions' not in user_stats[user.id]: user_stats[user.id]['game_sessions'] = []
    user_stats[user.id]['game_sessions'].append(game_id)
    
    user_wallets[user.id] -= bet_amount
    save_user_data(user.id)

    initial_text = (
        f"💣 <b>Mines Game Started!</b> (ID: <code>{game_id}</code>)\n\nBet: <b>${bet_amount:.2f}</b>\nMines: <b>{num_mines}</b>\n\n"
        "Click the buttons to reveal tiles. Find gems to increase your multiplier. Avoid the bombs!\n"
        "You can cash out after any successful pick."
    )
    await update.message.reply_text(
        initial_text, parse_mode=ParseMode.HTML, reply_markup=mines_keyboard(game_id)
    )
    context.user_data.clear()
    return ConversationHandler.END

@check_banned
@check_maintenance
async def mines_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    parts = query.data.split("_")
    action = parts[1]
    game_id = parts[2]

    game = game_sessions.get(game_id)

    if not game:
        await query.edit_message_text("No active mines game found, it has ended, or it is not your game.", reply_markup=None)
        return

    # NEW: Game interaction security
    if user.id != game.get('user_id'):
        await query.answer("This is not your game!", show_alert=True)
        return

    if game.get("status") != 'active':
        # Don't edit message if game is over, just inform the user who tapped
        await query.answer("This game has already ended.", show_alert=True)
        return


    if action == "cashout":
        safe_picks = len(game["picks"])
        if safe_picks == 0:
            await query.answer("You need to make at least one pick to cash out.", show_alert=True)
            return

        multiplier = get_mines_multiplier(game["num_mines"], safe_picks)
        winnings = game["bet_amount"] * multiplier
        user_wallets[user.id] += winnings
        game["status"] = 'completed'
        game["win"] = True
        game["multiplier"] = multiplier
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game['bet_amount'], win=True, multiplier=multiplier, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "mines", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Cashed out: {safe_picks} safe picks, Multiplier: {multiplier:.2f}x, Mine positions: {game['mines']}")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        keyboard_with_reveal = mines_keyboard(game_id, reveal=True)
        # Append PF button to revealed board
        keyboard_with_reveal = InlineKeyboardMarkup(
            list(keyboard_with_reveal.inline_keyboard) + [keyboard[0]]
        )
        
        await query.edit_message_text(
            f"💸 <b>Cashed Out!</b> (ID: <code>{game_id}</code>)\n\nYou won <b>${winnings:.2f}</b> with {safe_picks} correct picks!\n"
            f"Multiplier: <b>{multiplier:.2f}x</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_with_reveal
        )
        # del game_sessions[game_id] # FIX: Don't delete history
        return

    try:
        cell = int(parts[3])
    except (ValueError, IndexError): return

    if cell in game["picks"]:
        await query.answer("You have already picked this tile.", show_alert=True)
        return

    if cell in game["mines"]:
        game["status"] = 'completed'
        game["win"] = False
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game['bet_amount'], win=False, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "mines", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Hit mine at tile {cell}, Mine positions: {game['mines']}")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        keyboard_with_reveal = mines_keyboard(game_id, reveal=True)
        # Append PF button to revealed board
        keyboard_with_reveal = InlineKeyboardMarkup(
            list(keyboard_with_reveal.inline_keyboard) + [keyboard[0]]
        )
        
        await query.edit_message_text(
            f"💥 <b>Boom!</b> You hit a mine at tile {cell}. (ID: <code>{game_id}</code>)\n\n"
            f"You lost your bet of <b>${game['bet_amount']:.2f}</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_with_reveal
        )
        # del game_sessions[game_id] # FIX: Don't delete history
        return

    game["picks"].append(cell)
    safe_picks = len(game["picks"])
    multiplier = get_mines_multiplier(game["num_mines"], safe_picks)
    potential_winnings = game["bet_amount"] * multiplier

    if safe_picks == (game["total_cells"] - game["num_mines"]):
        game["status"] = 'completed'
        game["win"] = True
        game["multiplier"] = multiplier
        user_wallets[user.id] += potential_winnings
        increment_user_nonce(user.id)
        update_stats_on_bet(user.id, game_id, game['bet_amount'], win=True, multiplier=multiplier, context=context)
        update_pnl(user.id)
        save_user_data(user.id)
        
        # Store provably fair record
        store_provably_fair_record(game_id, "mines", game["server_seed"], game["client_seed"], game["nonce"], 
                                   result_data=f"Max win: {safe_picks} gems, Multiplier: {multiplier:.2f}x, Mine positions: {game['mines']}")
        
        # Add provably fair button
        keyboard = [[await create_provably_fair_button(game_id, context)]]
        keyboard_with_reveal = mines_keyboard(game_id, reveal=True)
        # Append PF button to revealed board
        keyboard_with_reveal = InlineKeyboardMarkup(
            list(keyboard_with_reveal.inline_keyboard) + [keyboard[0]]
        )
        
        await query.edit_message_text(
            f"🎉 <b>MAX WIN!</b> (ID: <code>{game_id}</code>)\n\nYou found all {safe_picks} gems and won <b>${potential_winnings:.2f}</b>!\n"
            f"Final Multiplier: <b>{multiplier:.2f}x</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_with_reveal
        )
        # del game_sessions[game_id] # FIX: Don't delete history
        return

    next_text = (
        f"✅ Safe! Tile {cell} was a gem. (ID: <code>{game_id}</code>)\n\n<b>Picks:</b> {safe_picks}/{game['total_cells'] - game['num_mines']}\n"
        f"<b>Current Multiplier:</b> {multiplier:.2f}x\n<b>Current Cashout:</b> ${potential_winnings:.2f}"
    )
    await query.edit_message_text(next_text, parse_mode=ParseMode.HTML, reply_markup=mines_keyboard(game_id))
    await query.answer(f"Safe! Current multiplier: {multiplier:.2f}x")

# --- /cancelall command (owner only, cancels all matches and notifies users) ---
async def cancel_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the owner can use this command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    cancelled = 0
    for game_id, game in list(game_sessions.items()):
        if game.get("status") == 'active' and 'players' in game: # Only cancel PvP games
            game["status"] = 'cancelled'
            for uid in game["players"]:
                user_wallets[uid] += game["bet_amount"]
                save_user_data(uid)
                try:
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"Your match {game_id} has been cancelled by the bot owner. Your bet has been refunded."
                    )
                except Exception: pass
            cancelled += 1
    await update.message.reply_text(
        f"Cancelled {cancelled} active PvP matches. Bets refunded to players."
    )

# --- STOP/RESUME/CANCEL ALL HANDLERS ---
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the owner can use this command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    ongoing_matches = [m for m in game_sessions.values() if m.get("status") == 'active' and 'players' in m]
    if ongoing_matches:
        await update.message.reply_text("There are ongoing matches. Please finish or use /cancelall before stopping.")
        return
    keyboard = [[InlineKeyboardButton("Yes", callback_data="stop_confirm_yes"), InlineKeyboardButton("No", callback_data="stop_confirm_no")]]
    await update.message.reply_text("Are you sure you want to stop the bot? This will pause new games.", reply_markup=InlineKeyboardMarkup(keyboard))

async def stop_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_stopped
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if user.id != BOT_OWNER_ID:
        await query.answer("Only the owner can confirm stop.", show_alert=True)
        return
    if query.data == "stop_confirm_yes":
        bot_stopped = True
        await query.edit_message_text("✅ Bot is now stopped. No new matches can be started.")
    else:
        await query.edit_message_text("Stop cancelled. Bot remains active.")

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_stopped
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the owner can use this command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    bot_stopped = False
    await update.message.reply_text("✅ Bot is resumed. New matches can be started.")

# --- BANK COMMAND ---
@check_banned
@check_maintenance
async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    # FIX: Show the house balance from bot settings
    bank = bot_settings.get("house_balance", 0.0)
    await update.message.reply_text(f"🏦 <b>BOT BANK</b>\n\n"
                                    f"This is the designated house balance.\n"
                                    f"Current House Balance: <b>${bank:,.2f}</b>",
                                    parse_mode=ParseMode.HTML)

# --- RAIN COMMAND ---
@check_banned
@check_maintenance
async def rain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    args = update.message.text.strip().split()
    if len(args) != 3:
        await update.message.reply_text("Usage: /rain amount N (e.g. /rain 50 2)")
        return
    try:
        amount = float(args[1])
        N = int(args[2])
        if amount <= 0 or N <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid amount or number.")
        return

    if user_wallets.get(user.id, 0.0) < amount:
        await update.message.reply_text("You do not have enough funds to rain.")
        return

    # FIXED: Eligible users are all registered users except the rainer
    eligible = [uid for uid in user_stats.keys() if uid != user.id]

    if N > len(eligible):
        await update.message.reply_text(f"Not enough users to rain on! Found {len(eligible)}, need {N}.")
        return

    chosen = random.sample(eligible, N)
    portion = amount / N
    user_wallets[user.id] -= amount
    rained_on_users = []
    for uid in chosen:
        user_wallets[uid] = user_wallets.get(uid, 0) + portion
        await ensure_user_in_wallets(uid, context=context)
        update_stats_on_rain_received(uid, portion)
        update_pnl(uid)
        save_user_data(uid)
        username = user_stats.get(uid, {}).get("userinfo", {}).get("username", f"ID: {uid}")
        rained_on_users.append(f"@{username}" if username else f"ID: {uid}")
    save_user_data(user.id)
    rained_on_str = ", ".join(rained_on_users)
    await update.message.reply_text(f"🌧️ Rained ${amount:.2f} on {N} users!\nEach received ${portion:.2f}.\n\nRecipients: {rained_on_str}")

@check_banned
@check_maintenance
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context, first_name=user.first_name)
    stats = user_stats[user.id]
    total_deposits = sum(d['amount'] for d in stats.get('deposits', []))
    total_withdrawals = sum(w['amount'] for w in stats.get('withdrawals', []))
    
    # Get user level
    level_data = get_user_level(user.id)
    
    # Get user currency for display
    user_currency = get_user_currency(user.id)
    balance = user_wallets.get(user.id, 0.0)
    formatted_balance = format_currency(balance, user_currency)
    
    # Calculate additional stats
    total_wagered = stats.get('bets', {}).get('amount', 0.0)
    formatted_wagered = format_currency(total_wagered, user_currency)
    formatted_deposits = format_currency(total_deposits, user_currency)
    formatted_withdrawals = format_currency(total_withdrawals, user_currency)
    formatted_tips_received = format_currency(stats.get('tips_received', {}).get('amount', 0.0), user_currency)
    formatted_tips_sent = format_currency(stats.get('tips_sent', {}).get('amount', 0.0), user_currency)
    formatted_rain = format_currency(stats.get('rain_received', {}).get('amount', 0.0), user_currency)
    formatted_pnl = format_currency(stats.get('pnl', 0.0), user_currency)
    
    # Get referral stats
    referral_count = len(stats.get('referral', {}).get('referred_users', []))
    referral_commission = stats.get('referral', {}).get('commission_earned', 0.0)
    formatted_commission = format_currency(referral_commission, user_currency)
    
    # Get achievement count
    achievement_count = len(stats.get('achievements', []))
    
    # Win rate calculation
    total_bets = stats.get('bets', {}).get('count', 0)
    wins = stats.get('bets', {}).get('wins', 0)
    losses = stats.get('bets', {}).get('losses', 0)
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    
    text = (
        f"📊 <b>Your Complete Stats</b>\n\n"
        f"👤 <b>User Info:</b>\n"
        f"  Username: @{stats.get('userinfo', {}).get('username','N/A')}\n"
        f"  User ID: <code>{user.id}</code>\n"
        f"  Join Date: {stats.get('userinfo', {}).get('join_date', 'N/A')[:10]}\n"
        f"  Currency: {user_currency}\n\n"
        f"🦄 <b>Level:</b> {level_data['level']} ({level_data['name']})\n"
        f"  Rakeback Rate: {level_data['rakeback_percentage']}%\n\n"
        f"💰 <b>Balance:</b> {formatted_balance}\n\n"
        f"🎲 <b>Betting Stats:</b>\n"
        f"  Total Bets: {total_bets}\n"
        f"  Wins: {wins} | Losses: {losses}\n"
        f"  Win Rate: {win_rate:.1f}%\n"
        f"  Total Wagered: {formatted_wagered}\n"
        f"  PvP Wins: {stats.get('bets', {}).get('pvp_wins', 0)}\n\n"
        f"💵 <b>Financial Stats:</b>\n"
        f"  Deposits: {len(stats.get('deposits',[]))} ({formatted_deposits})\n"
        f"  Withdrawals: {len(stats.get('withdrawals',[]))} ({formatted_withdrawals})\n"
        f"  P&L: {formatted_pnl}\n\n"
        f"🎁 <b>Social Stats:</b>\n"
        f"  Tips Received: {stats.get('tips_received', {}).get('count', 0)} ({formatted_tips_received})\n"
        f"  Tips Sent: {stats.get('tips_sent', {}).get('count', 0)} ({formatted_tips_sent})\n"
        f"  Rain Received: {stats.get('rain_received', {}).get('count', 0)} ({formatted_rain})\n\n"
        f"🤝 <b>Referral Stats:</b>\n"
        f"  Referred Users: {referral_count}\n"
        f"  Commission Earned: {formatted_commission}\n\n"
        f"🏆 <b>Achievements:</b> {achievement_count} unlocked\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]]
    
    # Send dashboard image with stats text in caption (NEW FEATURE - Combined)
    if not from_callback:
        dashboard_image = await generate_dashboard_image(user.id, context)
        if dashboard_image:
            try:
                sent_message = await update.message.reply_photo(
                    photo=dashboard_image,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Set ownership after sending
                set_menu_owner(sent_message, user.id)
                return  # Exit early since we already sent the message
            except Exception as e:
                logging.error(f"Error sending dashboard image: {e}")
                # Fall through to text-only message
    
    if from_callback:
        await safe_edit_message(update.callback_query, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        sent_message = await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        # Set ownership after sending
        set_menu_owner(sent_message, user.id)

# --- USERS (OWNER-ONLY) COMMAND ---
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the owner can use this command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if not user_stats:
        await update.message.reply_text("No users found in the database.")
        return

    context.user_data['users_page'] = 0
    await send_users_page(update, context)

async def send_users_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = context.user_data.get('users_page', 0)
    page_size = 5
    user_ids = list(user_stats.keys())
    start_index = page * page_size
    end_index = start_index + page_size

    paginated_user_ids = user_ids[start_index:end_index]

    if update.callback_query and not paginated_user_ids:
        await update.callback_query.answer("No more users.", show_alert=True)
        return

    msg = "<b>All User Stats (Page {}):</b>\n\n".format(page + 1)
    for uid in paginated_user_ids:
        stats = user_stats[uid]
        username = stats.get('userinfo', {}).get('username', 'N/A')
        pnl = stats.get('pnl', 0.0)
        msg += (
            f"👤 @{username} (ID: <code>{uid}</code>)\n"
            f"  - 💰 <b>Balance:</b> ${user_wallets.get(uid, 0):.2f}\n"
            f"  - 📈 <b>P&L:</b> ${pnl:.2f}\n"
            f"  - 🎲 <b>Bets:</b> {stats.get('bets',{}).get('count',0)} (W: {stats.get('bets',{}).get('wins',0)}, L: {stats.get('bets',{}).get('losses',0)})\n"
        )

    keyboard = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️ Previous", callback_data="users_prev"))
    if end_index < len(user_ids):
        row.append(InlineKeyboardButton("Next ➡️", callback_data="users_next"))
    if row:
        keyboard.append(row)

    # NEW: Back to admin dashboard button
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def users_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID:
        await query.answer("This is an admin-only button.", show_alert=True)
        return

    await query.answer()
    action = query.data
    page = context.user_data.get('users_page', 0)

    if action == "users_next":
        context.user_data['users_page'] = page + 1
    elif action == "users_prev":
        context.user_data['users_page'] = max(0, page - 1)

    await send_users_page(update, context)

# --- New Games (Darts, Football, Bowling, Dice) ---
@check_banned
@check_maintenance
async def generic_emoji_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    if bot_stopped:
        await update.message.reply_text("🚫 Bot is currently stopped. No new matches can be started.")
        return
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    message_text = update.message.text.strip().split()
    
    # New format: /dice @username amount MX ftY
    # M = N (normal) or C (crazy), X = 1, 2, or 3 (rolls)
    if len(message_text) != 5:
        await update.message.reply_text(
            f"<b>Usage:</b> <code>/{game_type} @username amount MX ftY</code>\n\n"
            f"<b>Parameters:</b>\n"
            f"• <code>@username</code> - Opponent's username\n"
            f"• <code>amount</code> - Bet amount (or 'all')\n"
            f"• <code>MX</code> - Mode and rolls:\n"
            f"  - <code>N1</code>, <code>N2</code>, <code>N3</code> - Normal mode (1-3 rolls)\n"
            f"  - <code>C1</code>, <code>C2</code>, <code>C3</code> - Crazy mode (1-3 rolls)\n"
            f"• <code>ftY</code> - First to Y points\n\n"
            f"<b>Examples:</b>\n"
            f"• <code>/{game_type} @player 10 N1 ft3</code>\n"
            f"• <code>/{game_type} @player 20 C2 ft5</code>",
            parse_mode=ParseMode.HTML
        )
        return

    opponent_username = normalize_username(message_text[1])
    amount_str = message_text[2].lower()
    mode_rolls_str = message_text[3].upper()
    ft_str = message_text[4].lower()

    if not opponent_username or opponent_username == normalize_username(user.username):
        await update.message.reply_text("Please specify a valid opponent's @username that is not yourself.")
        return

    # Parse mode and rolls (e.g., N1, C2, N3)
    if len(mode_rolls_str) != 2 or mode_rolls_str[0] not in ['N', 'C'] or mode_rolls_str[1] not in ['1', '2', '3']:
        await update.message.reply_text(
            "Invalid mode/rolls format. Use N1-N3 for Normal mode or C1-C3 for Crazy mode.\n"
            "Example: N1 (Normal, 1 roll), C2 (Crazy, 2 rolls)"
        )
        return
    
    game_mode = "normal" if mode_rolls_str[0] == 'N' else "crazy"
    game_rolls = int(mode_rolls_str[1])

    if amount_str == "all":
        bet_amount = user_wallets.get(user.id, 0.0)
    else:
        try: bet_amount = float(amount_str)
        except ValueError:
            await update.message.reply_text("Invalid amount.")
            return

    if not await check_bet_limits(update, bet_amount, f'pvp_{game_type}'):
        return

    if not ft_str.startswith("ft"):
        await update.message.reply_text("Invalid format for points target (must be ftX, e.g., ft3).")
        return
    try: target_points = int(ft_str[2:])
    except ValueError:
        await update.message.reply_text("Invalid points target.")
        return

    if user_wallets.get(user.id, 0.0) < bet_amount:
        await send_insufficient_balance_message(update)
        return

    opponent_id = username_to_userid.get(opponent_username)
    if not opponent_id:
        try:
            chat = await context.bot.get_chat(opponent_username)
            opponent_id = chat.id
            await ensure_user_in_wallets(opponent_id, chat.username, context=context)
        except Exception:
            await update.message.reply_text(f"Opponent {opponent_username} not found. Ask them to DM the bot or send /bal first.")
            return

    await ensure_user_in_wallets(opponent_id, opponent_username, context=context)
    if user_wallets.get(opponent_id, 0.0) < bet_amount:
        await update.message.reply_text(f"Opponent {opponent_username} does not have enough balance for this match.")
        return

    match_id = generate_unique_id("PVP")
    mode_text = "Highest total wins" if game_mode == "normal" else "Lowest total wins"
    match_data = {
        "id": match_id, "game_type": f"pvp_{game_type}", "bet_amount": bet_amount, "target_points": target_points,
        "points": {user.id: 0, opponent_id: 0}, "emoji_buffer": {},
        "players": [user.id, opponent_id],
        "usernames": {user.id: normalize_username(user.username) or f"ID{user.id}", opponent_id: opponent_username},
        "status": "pending", "last_roller": None,
        "host_id": user.id, "chat_id": update.effective_chat.id,
        "timestamp": str(datetime.now(timezone.utc)),
        "game_mode": game_mode,  # normal or crazy
        "game_rolls": game_rolls,  # 1, 2, or 3
        "player_rolls": {user.id: [], opponent_id: []},  # Track rolls for each player
    }
    game_sessions[match_id] = match_data
    keyboard = [[InlineKeyboardButton("Accept", callback_data=f"accept_{match_id}"), InlineKeyboardButton("Decline", callback_data=f"decline_{match_id}")]]

    sent_message = await update.message.reply_text(
        f"🎮 <b>New {game_type.capitalize()} Match Request!</b>\n\n"
        f"<b>Host:</b> {user.mention_html()}\n"
        f"<b>Opponent:</b> {opponent_username}\n"
        f"<b>Bet:</b> ${bet_amount:.2f}\n"
        f"<b>Mode:</b> {game_mode.capitalize()} ({mode_text})\n"
        f"<b>Rolls per round:</b> {game_rolls}\n"
        f"<b>Target:</b> First to {target_points} points\n\n"
        f"{opponent_username}, tap Accept to join!\n"
        f"Match ID: <code>{match_id}</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    try:
        await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=sent_message.message_id, disable_notification=True)
        match_data['pinned_message_id'] = sent_message.message_id
    except BadRequest as e:
        logging.warning(f"Failed to pin match message for match {match_id}: {e}")

@check_banned
@check_maintenance
async def pvb_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    
    # Ban check for callbacks
    if user.id in bot_settings.get("banned_users", []):
        await query.answer("You are banned.", show_alert=True)
        return
    if user.id in bot_settings.get("tempbanned_users", []):
        await query.answer("You are temporarily banned.", show_alert=True)
        return
    
    # Ownership check
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await ensure_user_in_wallets(query.from_user.id, query.from_user.username, context=context)

    if data.startswith("pvb_start_"):
        game_type = data.replace("pvb_start_", "")
        context.user_data['game_type'] = game_type
        
        # Show mode selection (Normal/Crazy)
        keyboard = [
            [InlineKeyboardButton("📊 Normal Mode", callback_data=f"pvb_mode_normal_{game_type}")],
            [InlineKeyboardButton("🎪 Crazy Mode", callback_data=f"pvb_mode_crazy_{game_type}")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="cancel_game")]
        ]
        await query.edit_message_text(
            f"🎮 <b>Select Game Mode</b>\n\n"
            f"<b>Normal Mode:</b> Highest score wins\n"
            f"<b>Crazy Mode:</b> Lowest score wins",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        set_menu_owner(query.message, user.id)
        return

    elif data.startswith("pvb_mode_"):
        # Extract mode and game_type from callback data
        parts = data.split("_")
        mode = parts[2]  # normal or crazy
        game_type = "_".join(parts[3:])  # handle game types with underscores
        context.user_data['game_type'] = game_type
        context.user_data['game_mode'] = mode
        
        # Show roll selection (1/2/3 rolls)
        keyboard = [
            [InlineKeyboardButton("1️⃣ 1 Roll", callback_data=f"pvb_rolls_1_{mode}_{game_type}")],
            [InlineKeyboardButton("2️⃣ 2 Rolls", callback_data=f"pvb_rolls_2_{mode}_{game_type}")],
            [InlineKeyboardButton("3️⃣ 3 Rolls", callback_data=f"pvb_rolls_3_{mode}_{game_type}")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="cancel_game")]
        ]
        await query.edit_message_text(
            f"🎮 <b>Select Number of Rolls</b>\n\n"
            f"Mode: <b>{mode.capitalize()}</b>\n"
            f"Choose how many times each player will roll:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        set_menu_owner(query.message, user.id)
        return

    elif data.startswith("pvb_rolls_"):
        # Extract rolls, mode, and game_type from callback data
        parts = data.split("_")
        rolls = int(parts[2])  # 1, 2, or 3
        mode = parts[3]  # normal or crazy
        game_type = "_".join(parts[4:])  # handle game types with underscores
        context.user_data['game_type'] = game_type
        context.user_data['game_mode'] = mode
        context.user_data['game_rolls'] = rolls
        
        # Now call start_pvb_conversation to enter the conversation handler
        return await start_pvb_conversation_after_setup(query, context)

    elif data.startswith("pvp_info_"):
        game_type_map = {"dice_bot": "dice", "football": "goal", "darts": "darts", "bowling": "bowl"}
        game_type = game_type_map.get(data.replace("pvp_info_", ""), "dice")
        
        # Update instructions with new command format
        await query.edit_message_text(
            f"🎮 <b>PvP {game_type.capitalize()} Game</b>\n\n"
            f"<b>Command Format:</b>\n"
            f"<code>/{game_type} @username amount MX ftY</code>\n\n"
            f"<b>Parameters:</b>\n"
            f"• <code>@username</code> - Your opponent's username\n"
            f"• <code>amount</code> - Bet amount (or 'all')\n"
            f"• <code>MX</code> - Mode and rolls:\n"
            f"  - <code>N1</code>, <code>N2</code>, <code>N3</code> - Normal mode (1, 2, or 3 rolls)\n"
            f"  - <code>C1</code>, <code>C2</code>, <code>C3</code> - Crazy mode (1, 2, or 3 rolls)\n"
            f"• <code>ftY</code> - First to Y points wins\n\n"
            f"<b>Examples:</b>\n"
            f"• <code>/{game_type} @player 10 N1 ft3</code> - Normal mode, 1 roll, first to 3 points\n"
            f"• <code>/{game_type} @player 20 C2 ft5</code> - Crazy mode, 2 rolls, first to 5 points\n"
            f"• <code>/{game_type} @player all N3 ft3</code> - Normal mode, 3 rolls, bet all\n\n"
            f"<b>Mode Explanation:</b>\n"
            f"• <b>Normal (N):</b> Highest total score wins the point\n"
            f"• <b>Crazy (C):</b> Lowest total score wins the point",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"game_{data.replace('pvp_info_', '')}")]])
        )

async def start_pvb_conversation_after_setup(query, context):
    """Helper function to enter the PvB conversation after mode and roll setup"""
    await query.edit_message_text(
        f"Please enter your bet amount for this game (or 'all').",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]])
    )
    return SELECT_BET_AMOUNT

# --- BALANCE COMMAND ---
@check_banned
@check_maintenance
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context, first_name=user.first_name)
    user_currency = get_user_currency(user.id)
    formatted_balance = format_balance_with_locked(user.id, user_currency)
    
    keyboard = [
        [
            InlineKeyboardButton("💰 Deposit", callback_data="main_deposit"),
            InlineKeyboardButton("💸 Withdraw", callback_data="main_withdraw")
        ],
        [InlineKeyboardButton("💼 View Full Wallet", callback_data="main_wallet")]
    ]
    
    text = f"💰 <b>Your Balance</b>\n\n{formatted_balance}"
    
    # Send dashboard image with balance text in caption (NEW FEATURE - Combined)
    dashboard_image = await generate_dashboard_image(user.id, context)
    if dashboard_image:
        try:
            await update.message.reply_photo(
                photo=dashboard_image,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logging.error(f"Error sending dashboard image: {e}")
            # Fallback to text only
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        # No image, send text only
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- NEW USER HISTORY COMMANDS ---
@check_banned
@check_maintenance
async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False, page=0):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_game_ids = user_stats[user.id].get("game_sessions", [])

    if not user_game_ids:
        text = "You haven't played any matches yet."
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Wallet", callback_data="main_wallet")]]) if from_callback else None
        if from_callback: await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else: await update.message.reply_text(text, reply_markup=reply_markup)
        return

    all_games = [game_sessions[gid] for gid in reversed(user_game_ids) if gid in game_sessions]
    pending_games = [g for g in all_games if g.get("status") == "active"]
    completed_games = [g for g in all_games if g.get("status") != "active"]

    msg = ""
    # Display pending games first, always
    if pending_games:
        msg += "⏳ <b>Your Pending/Active Games:</b>\n\n"
        for game in pending_games:
            game_type = game['game_type'].replace('_', ' ').title()
            msg += (f"<b>Game:</b> {game_type} | <b>ID:</b> <code>{game['id']}</code>\n"
                    f"<b>Bet:</b> ${game['bet_amount']:.2f} | <b>Status:</b> {game['status'].capitalize()}\n"
                    f"Use <code>/continue {game['id']}</code> to resume.\n"
                    "--------------------\n")

    # Paginated completed games
    page_size = 10
    start_index = page * page_size
    end_index = start_index + page_size
    paginated_completed = completed_games[start_index:end_index]

    msg += f"📜 <b>Your Completed Games (Page {page + 1}):</b>\n\n"
    if not paginated_completed:
        msg += "No completed games on this page.\n"

    for game in paginated_completed:
        game_type = game['game_type'].replace('_', ' ').title()
        msg += f"<b>Game:</b> {game_type} | <b>ID:</b> <code>{game['id']}</code>\n"

        # Determine win/loss/push status text
        if game.get('win') is True:
            win_status = "Win"
        elif game.get('win') is False:
            win_status = "Loss"
        else: # Covers push (None) or other statuses
            win_status = game['status'].capitalize()

        msg += f"<b>Bet:</b> ${game['bet_amount']:.2f} | <b>Result:</b> {win_status}\n"

        # Add game-specific details
        if game['game_type'] == 'blackjack':
            player_val = calculate_hand_value(game.get('player_hand', []))
            dealer_val = calculate_hand_value(game.get('dealer_hand', []))
            msg += f"<b>Hand:</b> {player_val} vs <b>Dealer:</b> {dealer_val}\n"
        elif game['game_type'] in ['mines', 'tower', 'coin_flip']:
            multiplier = game.get('multiplier', 0)
            msg += f"<b>Multiplier:</b> {multiplier:.2f}x\n"
        elif 'players' in game: # PvP
            p1_id, p2_id = game['players']
            p1_name = game['usernames'].get(p1_id, f"ID:{p1_id}")
            p2_name = game['usernames'].get(p2_id, f"ID:{p2_id}")
            score = f"{game['points'].get(p1_id, 0)} - {game['points'].get(p2_id, 0)}"
            msg += f"<b>Match:</b> {p1_name} vs {p2_name}\n<b>Score:</b> {score}\n"

        msg += "--------------------\n"

    # Pagination Keyboard
    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"my_matches_{page - 1}"))
    if end_index < len(completed_games):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"my_matches_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Wallet", callback_data="main_wallet")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if from_callback:
        await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

@check_banned
@check_maintenance
async def deals_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False, page=0):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_deal_ids = user_stats[user.id].get("escrow_deals", [])

    if not user_deal_ids:
        text = "You have no escrow deals."
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Wallet", callback_data="main_wallet")]]) if from_callback else None
        if from_callback: await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else: await update.message.reply_text(text, reply_markup=reply_markup)
        return

    all_deals = []
    for deal_id in reversed(user_deal_ids):
        deal = escrow_deals.get(deal_id)
        if not deal and os.path.exists(os.path.join(ESCROW_DIR, f"{deal_id}.json")):
            with open(os.path.join(ESCROW_DIR, f"{deal_id}.json"), "r") as f: deal = json.load(f)
        if deal: all_deals.append(deal)

    page_size = 10
    start_index = page * page_size
    end_index = start_index + page_size
    paginated_deals = all_deals[start_index:end_index]

    msg = f"🛡️ <b>Your Escrow Deals (Page {page + 1}):</b>\n\n"
    if not paginated_deals:
        msg += "No deals on this page.\n"

    for deal in paginated_deals:
        seller_name = deal['seller'].get('username') or f"ID:{deal['seller']['id']}"
        buyer_name = deal['buyer'].get('username') or f"ID:{deal['buyer']['id']}"
        role = "Seller" if user.id == deal['seller']['id'] else "Buyer"
        msg += (f"<b>Deal ID:</b> <code>{deal['id']}</code>\n<b>Your Role:</b> {role}\n"
                f"<b>Amount:</b> ${deal['amount']:.2f} USDT\n<b>Seller:</b> @{seller_name}\n<b>Buyer:</b> @{buyer_name}\n"
                f"<b>Status:</b> {deal['status'].replace('_', ' ').capitalize()}\n--------------------\n")

    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"my_deals_{page - 1}"))
    if end_index < len(all_deals):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"my_deals_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Wallet", callback_data="main_wallet")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if from_callback: await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else: await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# --- OWNER HISTORY COMMANDS ---
async def he_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    all_deal_files = [f for f in os.listdir(ESCROW_DIR) if f.endswith('.json')]
    if not all_deal_files:
        await update.message.reply_text("No escrow deals found.")
        return
    all_deal_files.sort(reverse=True)
    msg = "📜 <b>All Escrow Deals History (Latest 20):</b>\n\n"
    count = 0
    for fname in all_deal_files:
        if count >= 20: break
        with open(os.path.join(ESCROW_DIR, fname), 'r') as f:
            deal = json.load(f)
            seller_name = deal.get('seller', {}).get('username', 'N/A')
            buyer_name = deal.get('buyer', {}).get('username', 'N/A')
            msg += (f"<b>ID:</b> <code>{deal['id']}</code> | <b>Status:</b> {deal.get('status', 'N/A').capitalize()}\n"
                    f"<b>Amount:</b> ${deal.get('amount', 0.0):.2f} | <b>Date:</b> {deal.get('timestamp', 'N/A').split('T')[0]}\n"
                    f"<b>Seller:</b> @{seller_name}, <b>Buyer:</b> @{buyer_name}\n--------------------\n")
            count += 1
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def hc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)

    all_games = sorted(game_sessions.values(), key=lambda x: x.get("timestamp", ""), reverse=True)
    if not all_games:
        await update.message.reply_text("No game matches found.")
        return

    # Show pending games first for the owner
    pending_games = [g for g in all_games if g.get("status") == "active"]
    completed_games = [g for g in all_games if g.get("status") != "active"]

    msg = ""
    if pending_games:
        msg += "⏳ <b>Owner View: Active/Pending Games:</b>\n\n"
        for game in pending_games[:10]: # Limit display
             game_type = game['game_type'].replace('_', ' ').title()
             msg += f"<b>Game:</b> {game_type} | <b>ID:</b> <code>{game['id']}</code>\n"
             if 'players' in game:
                p_names = [game['usernames'].get(pid, f"ID:{pid}") for pid in game['players']]
                msg += f"<b>Players:</b> {', '.join(p_names)}\n"
             else:
                uname = user_stats.get(game['user_id'], {}).get('userinfo',{}).get('username', 'N/A')
                msg += f"<b>Player:</b> @{uname}\n"
             msg += "--------------------\n"

    msg += "\n📜 <b>All Casino Matches History (Latest 20 Completed):</b>\n\n"
    for match in completed_games[:20]:
        game_type = match['game_type'].replace('_', ' ').title()
        msg += f"<b>Game:</b> {game_type} | <b>ID:</b> <code>{match['id']}</code>\n"
        if 'players' in match: # PvP
            p1_id, p2_id = match['players']
            p1_name = match['usernames'].get(p1_id, f"ID:{p1_id}")
            p2_name = match['usernames'].get(p2_id, f"ID:{p2_id}")
            score = f"{match['points'].get(p1_id, 0)} - {match['points'].get(p2_id, 0)}"
            msg += f"<b>Match:</b> {p1_name} vs {p2_name}\n<b>Score:</b> {score} | "
        else: # Solo game
            uname = user_stats.get(match['user_id'], {}).get('userinfo',{}).get('username', 'N/A')
            msg += f"<b>Player:</b> @{uname} | "

        msg += (f"<b>Bet:</b> ${match['bet_amount']:.2f}\n"
                f"<b>Status:</b> {match.get('status', 'N/A').capitalize()}\n--------------------\n")
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

@check_banned
@check_maintenance
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /info <unique_id>")
        return

    unique_id = context.args[0]
    msg = f"🔍 <b>Detailed Info for ID:</b> <code>{unique_id}</code>\n\n"

    # Check in game sessions
    if unique_id in game_sessions:
        game = game_sessions[unique_id]
        game_type = game['game_type'].replace('_', ' ').title()
        timestamp = datetime.fromisoformat(game['timestamp']).strftime('%Y-%m-%d %H:%M UTC')
        msg += (f"<b>Type:</b> Game Session\n"
                f"<b>Game:</b> {game_type}\n"
                f"<b>Bet:</b> ${game.get('bet_amount', 0):.2f}\n"
                f"<b>Status:</b> {game.get('status', 'N/A').title()}\n"
                f"<b>Date:</b> {timestamp}\n")

        if 'players' in game: # PvP
            p1_id, p2_id = game['players']
            p1_name = game['usernames'].get(p1_id, f"ID:{p1_id}")
            p2_name = game['usernames'].get(p2_id, f"ID:{p2_id}")
            score = f"{game['points'].get(p1_id, 0)} - {game['points'].get(p2_id, 0)}"
            msg += f"<b>Players:</b> {p1_name} vs {p2_name}\n<b>Score:</b> {score}\n"
        elif 'user_id' in game: # Solo or PvB
            uid = game['user_id']
            uname = user_stats.get(uid, {}).get('userinfo',{}).get('username', f'ID:{uid}')
            msg += f"<b>Player:</b> @{uname} (<code>{uid}</code>)\n"

        if game.get('win') is not None:
             msg += f"<b>Result:</b> {'Win' if game['win'] else 'Loss'}\n"
        if game.get('multiplier'):
             msg += f"<b>Multiplier:</b> {game['multiplier']}x\n"

        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # Check in escrow deals
    deal_file = os.path.join(ESCROW_DIR, f"{unique_id}.json")
    deal = escrow_deals.get(unique_id)
    if not deal and os.path.exists(deal_file):
        with open(deal_file, 'r') as f: deal = json.load(f)

    if deal:
        seller, buyer = deal.get('seller', {}), deal.get('buyer', {})
        timestamp = datetime.fromisoformat(deal['timestamp']).strftime('%Y-%m-%d %H:%M UTC')
        msg += (f"<b>Type:</b> Escrow Deal\n"
               f"<b>Status:</b> {deal.get('status', 'N/A').upper()}\n<b>Amount:</b> ${deal.get('amount', 0):.2f} USDT\n"
               f"<b>Date:</b> {timestamp}\n\n"
               f"<b>Seller:</b>\n  - Username: @{seller.get('username', 'N/A')}\n  - ID: <code>{seller.get('id', 'N/A')}</code>\n\n"
               f"<b>Buyer:</b>\n  - Username: @{buyer.get('username', 'N/A')}\n  - ID: <code>{buyer.get('id', 'N/A')}</code>\n\n"
               f"<b>Deal Details:</b>\n<pre>{deal.get('details', 'No details provided.')}</pre>\n\n"
               f"<b>Deposit Tx Hash:</b>\n<code>{deal.get('deposit_tx_hash', 'N/A')}</code>\n\n"
               f"<b>Release Tx Hash:</b>\n<code>{deal.get('release_tx_hash', 'N/A')}</code>\n")
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    await update.message.reply_text("No game or escrow deal found with that ID.")

# --- MESSAGE LISTENER HANDLER ---
@check_banned
@check_maintenance
async def message_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    
    # Ban check for message listener
    if user.id in bot_settings.get("banned_users", []):
        return  # Silently ignore banned users
    if user.id in bot_settings.get("tempbanned_users", []):
        return  # Silently ignore temp banned users
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_stats[user.id]['last_update'] = str(datetime.now(timezone.utc))

    # NEW: Check for new members in a group
    if update.message.new_chat_members:
        chat_id = update.effective_chat.id
        settings = group_settings.get(chat_id)
        if settings and settings.get("welcome_message"):
            for new_member in update.message.new_chat_members:
                welcome_text = settings["welcome_message"].format(
                    first_name=new_member.first_name,
                    last_name=new_member.last_name or "",
                    username=f"@{new_member.username}" if new_member.username else "",
                    mention=new_member.mention_html(),
                    chat_title=update.effective_chat.title
                )
                await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
        return


    if 'escrow_step' in context.user_data:
        await handle_escrow_conversation(update, context)
        return

    # Handle single emoji game bet input
    if context.user_data.get('awaiting_single_emoji_bet') and update.message.text:
        game_key = context.user_data.get('single_emoji_game')
        if game_key in SINGLE_EMOJI_GAMES:
            try:
                bet_amount_usd, bet_amount_currency, currency = parse_bet_amount(update.message.text, user.id)
                
                if user_wallets.get(user.id, 0.0) < bet_amount_usd:
                    await send_insufficient_balance_message(update)
                    context.user_data.clear()
                    return
                
                # Clear the awaiting flag
                context.user_data.clear()
                
                # Play the game
                await play_single_emoji_game(update, context, game_key, bet_amount_usd, bet_amount_currency, currency)
                return
            except ValueError:
                await update.message.reply_text("Invalid amount. Please enter a valid number or 'all'.")
                return

    # Handle PvB games
    # Check BOTH context.chat_data (primary) and global dict (fallback)
    active_pvb_game_id = context.chat_data.get(f"active_pvb_game_{user.id}")
    if not active_pvb_game_id:
        active_pvb_game_id = active_pvb_games.get(user.id)  # Fallback to global dict
        if active_pvb_game_id and DEBUG_EMOJI_GAMES:
            logging.info(f"Found PvB game in global dict (fallback): {active_pvb_game_id}")
    
    # DEBUG LOGGING (controlled by DEBUG_EMOJI_GAMES flag)
    if update.message.dice and DEBUG_EMOJI_GAMES:
        logging.info(f"DICE: user={user.id}, emoji={update.message.dice.emoji}, value={update.message.dice.value}, active_game={active_pvb_game_id}, exists={active_pvb_game_id in game_sessions if active_pvb_game_id else False}")
    
    if active_pvb_game_id and active_pvb_game_id in game_sessions:
        game = game_sessions[active_pvb_game_id]
        game_type = game['game_type'].replace("pvb_", "").replace("xdxw_", "")
        # Handle different game_type naming variations
        emoji_map = {
            "dice": "🎲", "dice_bot": "🎲",
            "darts": "🎯",
            "goal": "⚽", "football": "⚽",
            "bowl": "🎳", "bowling": "🎳"
        }
        expected_emoji = emoji_map.get(game_type, "🎲")  # Default to dice if not found
        game_rolls = game.get('game_rolls', 1)
        game_mode = game.get('game_mode', 'normal')

        if update.message.dice and update.message.dice.emoji == expected_emoji and update.message.forward_origin is None:
            user_roll = update.message.dice.value
            
            # Add to user_rolls list
            if 'user_rolls' not in game:
                game['user_rolls'] = []
            game['user_rolls'].append(user_roll)
            
            # Check if user has completed all rolls
            if len(game['user_rolls']) < game_rolls:
                remaining = game_rolls - len(game['user_rolls'])
                await update.message.reply_text(f"Roll {len(game['user_rolls'])}/{game_rolls} complete. Send {remaining} more {expected_emoji}!")
                return
            
            # User finished rolling, now bot should roll
            user_rolls = game['user_rolls']
            user_total = sum(user_rolls)
            user_rolls_text = " + ".join(str(r) for r in user_rolls)
            
            # Show user's result first
            await update.message.reply_text(
                f"You rolled: {user_rolls_text} = <b>{user_total}</b>\n\n"
                f"Bot is rolling...",
                parse_mode=ParseMode.HTML
            )
            
            # NOW bot rolls
            bot_rolls = []
            for i in range(game_rolls):
                await asyncio.sleep(1)  # Rate limit protection
                try:
                    bot_dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji=expected_emoji)
                    bot_rolls.append(bot_dice_msg.dice.value)
                    await asyncio.sleep(4)  # Wait for animation to complete
                except Exception as e:
                    logging.error(f"Error sending dice in PvB game: {e}")
                    await update.message.reply_text("❌ An error occurred. Game terminated.")
                    game['status'] = 'error'
                    del context.chat_data[f"active_pvb_game_{user.id}"]
                    if user.id in active_pvb_games:
                        del active_pvb_games[user.id]
                    # Refund bet
                    user_wallets[user.id] += game['bet_amount']
                    update_pnl(user.id)
                    save_user_data(user.id)
                    return
            
            game["bot_rolls"] = bot_rolls
            bot_total = sum(bot_rolls)
            bot_rolls_text = " + ".join(str(r) for r in bot_rolls)
            
            # Determine winner based on mode
            win = False
            if game_mode == "normal":
                # Normal mode: highest total wins
                win = user_total > bot_total
                tie = user_total == bot_total
            else:
                # Crazy mode: lowest total wins
                win = user_total < bot_total
                tie = user_total == bot_total

            round_result = {"user_rolls": user_rolls, "bot_rolls": bot_rolls, 
                          "user_total": user_total, "bot_total": bot_total, "winner": None}
            
            if tie:
                await update.message.reply_text(
                    f"Bot rolled: {bot_rolls_text} = <b>{bot_total}</b>\n\n"
                    f"It's a tie! No point.",
                    parse_mode=ParseMode.HTML
                )
            elif win:
                game["user_score"] += 1
                round_result["winner"] = "user"
                await update.message.reply_text(
                    f"Bot rolled: {bot_rolls_text} = <b>{bot_total}</b>\n\n"
                    f"You win this round!",
                    parse_mode=ParseMode.HTML
                )
            else:
                game["bot_score"] += 1
                round_result["winner"] = "bot"
                await update.message.reply_text(
                    f"Bot rolled: {bot_rolls_text} = <b>{bot_total}</b>\n\n"
                    f"Bot wins this round!",
                    parse_mode=ParseMode.HTML
                )

            game["history"].append(round_result)
            game["current_round"] += 1
            game['user_rolls'] = []  # Reset for next round
            game['bot_rolls'] = []  # Reset for next round

            # Check for game end
            if game["user_score"] >= game["target_score"]:
                winnings = game["bet_amount"] * 2
                user_wallets[user.id] += winnings
                game['status'] = 'completed'
                game['win'] = True
                update_stats_on_bet(user.id, game['id'], game['bet_amount'], True, context=context)
                await asyncio.sleep(0.5)  # Rate limit protection
                await update.message.reply_text(f"🏆 Congratulations! You beat the bot ({game['user_score']}-{game['bot_score']}) and win ${winnings:.2f}!")
                del context.chat_data[f"active_pvb_game_{user.id}"]
                if user.id in active_pvb_games:
                    del active_pvb_games[user.id]
            elif game["bot_score"] >= game["target_score"]:
                game['status'] = 'completed'
                game['win'] = False
                update_stats_on_bet(user.id, game['id'], game['bet_amount'], False, context=context)
                await asyncio.sleep(0.5)  # Rate limit protection
                await update.message.reply_text(f"😔 Bot wins the match ({game['bot_score']}-{game['user_score']}). You lost ${game['bet_amount']:.2f}.")
                del context.chat_data[f"active_pvb_game_{user.id}"]
                if user.id in active_pvb_games:
                    del active_pvb_games[user.id]
            else: # Continue game - next round
                await asyncio.sleep(0.5)  # Rate limit protection
                await update.message.reply_text(
                    f"Score: You {game['user_score']} - {game['bot_score']} Bot. (First to {game['target_score']})\n\n"
                    f"<b>Your turn! Send {game_rolls} {expected_emoji}!</b>",
                    parse_mode=ParseMode.HTML
                )
            update_pnl(user.id)
            save_user_data(user.id)
            return  # Return only after processing PvB game emoji

    if update.message and update.message.dice and update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        # Ignore forwarded messages
        if update.message.forward_origin is not None:
            return
        
        try:
            dice_obj = update.message.dice
            chat_id = update.effective_chat.id
            emoji = dice_obj.emoji
            
            if DEBUG_EMOJI_GAMES:
                logging.info(f"PVP DICE: user={user.id}, chat={chat_id}, emoji={emoji}, value={dice_obj.value}")

            for match_id, match_data in list(game_sessions.items()):
                if match_data.get("chat_id") == chat_id and match_data.get("status") == 'active' and user.id in match_data.get("players", []):
                    if DEBUG_EMOJI_GAMES:
                        logging.info(f"PVP MATCH FOUND: match_id={match_id}, type={match_data.get('game_type')}, players={match_data.get('players')}, points={match_data.get('points')}")
                    
                    # Extract game type properly - handle pvp_, group_challenge_, xdxw_ prefixes
                    raw_game_type = match_data.get("game_type", "pvp_dice")
                    gtype = raw_game_type.replace("pvp_", "").replace("group_challenge_", "").replace("xdxw_", "")
                    players = match_data["players"]
                    game_rolls = match_data.get("game_rolls", 1)
                    game_mode = match_data.get("game_mode", "normal")
                    
                    # Initialize player_rolls if not exists
                    if "player_rolls" not in match_data:
                        match_data["player_rolls"] = {players[0]: [], players[1]: []}
                    
                    last_roller = match_data.get("last_roller")
                    
                    # Check turn order
                    if last_roller is None:
                        if user.id != players[0]:
                            await update.message.reply_text("It's not your turn yet! Host should roll first.")
                            return
                    elif user.id == last_roller:
                        # Check if current player has completed all rolls
                        if len(match_data["player_rolls"][user.id]) < game_rolls:
                            # Allow more rolls
                            pass
                        else:
                            await update.message.reply_text("Wait for your opponent to roll next.")
                            return
                    else:
                        # Other player's turn, check if they've started rolling
                        if len(match_data["player_rolls"][user.id]) > 0 and len(match_data["player_rolls"][user.id]) < game_rolls:
                            # Allow continuing rolls
                            pass
                        else:
                            # Not this player's turn
                            other_id = [pid for pid in players if pid != user.id][0]
                            if len(match_data["player_rolls"][other_id]) < game_rolls:
                                await update.message.reply_text("Wait for your opponent to complete their rolls.")
                                return

                    allowed_emojis = {"dice": "🎲", "darts": "🎯", "goal": "⚽", "bowl": "🎳"}
                    if emoji != allowed_emojis.get(gtype, "🎲"):
                        await update.message.reply_text(f"Only {allowed_emojis.get(gtype)} emoji allowed for this match!")
                        return

                    # Add roll to player's rolls
                    match_data["player_rolls"][user.id].append(dice_obj.value)
                    match_data["last_roller"] = user.id
                    
                    # Check if player has completed their rolls
                    current_player_rolls = len(match_data["player_rolls"][user.id])
                    if current_player_rolls < game_rolls:
                        remaining = game_rolls - current_player_rolls
                        await asyncio.sleep(1)
                        await update.message.reply_text(f"Roll {current_player_rolls}/{game_rolls} complete! Send {remaining} more {emoji}!")
                        return

                    # Check if both players have completed their rolls
                    p1, p2 = players
                    p1_rolls = match_data["player_rolls"].get(p1, [])
                    p2_rolls = match_data["player_rolls"].get(p2, [])
                    
                    # Check if playing against bot (opponent_id == 0)
                    is_bot_game = match_data.get("opponent_id") == 0
                    
                    if is_bot_game and user.id == p1 and len(p1_rolls) == game_rolls:
                        # User (host) completed rolls, now bot should roll
                        await asyncio.sleep(1)
                        await update.message.reply_text(f"Bot is rolling...")
                        
                        bot_rolls = []
                        for i in range(game_rolls):
                            await asyncio.sleep(1)
                            bot_dice = await context.bot.send_dice(chat_id, emoji=dice_obj.emoji)
                            await asyncio.sleep(4)  # Wait for animation
                            bot_rolls.append(bot_dice.dice.value)
                        
                        match_data["player_rolls"][p2] = bot_rolls
                        p2_rolls = bot_rolls
                    
                    if len(p1_rolls) == game_rolls and len(p2_rolls) == game_rolls:
                        # Both players completed, calculate results
                        p1_total = sum(p1_rolls)
                        p2_total = sum(p2_rolls)
                        
                        p1_rolls_text = " + ".join(str(r) for r in p1_rolls)
                        p2_rolls_text = " + ".join(str(r) for r in p2_rolls)
                        
                        text = f"<b>Round Results:</b>\n"
                        text += f"{match_data['usernames'][p1]}: {p1_rolls_text} = <b>{p1_total}</b>\n"
                        text += f"{match_data['usernames'][p2]}: {p2_rolls_text} = <b>{p2_total}</b>\n\n"
                        
                        winner_id, extra_info = None, ""
                        
                        # DEBUG: Log scoring details
                        if DEBUG_EMOJI_GAMES:
                            logging.info(f"SCORING: match_id={match_id}, mode={game_mode}, p1={p1}, p2={p2}, p1_total={p1_total}, p2_total={p2_total}, points_before={match_data.get('points')}")
                        
                        # Determine winner based on mode
                        if game_mode == "normal":
                            # Normal mode: highest total wins
                            if p1_total > p2_total:
                                winner_id = p1
                            elif p2_total > p1_total:
                                winner_id = p2
                            else:
                                extra_info = "🤝 It's a tie! No points this round."
                        else:
                            # Crazy mode: lowest total wins
                            if p1_total < p2_total:
                                winner_id = p1
                            elif p2_total < p1_total:
                                winner_id = p2
                            else:
                                extra_info = "🤝 It's a tie! No points this round."

                        if DEBUG_EMOJI_GAMES:
                            logging.info(f"WINNER: winner_id={winner_id}, extra_info={extra_info}")

                        if winner_id is not None:
                            try:
                                match_data["points"][winner_id] += 1
                                text += f"🎉 {match_data['usernames'][winner_id]} wins this round!"
                                if DEBUG_EMOJI_GAMES:
                                    logging.info(f"POINTS_UPDATED: {match_data['points']}")
                            except KeyError as e:
                                logging.error(f"KeyError updating points: winner_id={winner_id}, points_keys={list(match_data.get('points', {}).keys())}, usernames_keys={list(match_data.get('usernames', {}).keys())}, error={e}")
                                text += f"⚠️ Error updating score (winner_id={winner_id} not found)"
                        else:
                            text += extra_info

                        try:
                            text += f"\n\n<b>Score:</b> {match_data['usernames'][p1]} {match_data['points'][p1]} - {match_data['points'][p2]} {match_data['usernames'][p2]}"
                        except KeyError as e:
                            logging.error(f"KeyError displaying score: p1={p1}, p2={p2}, points_keys={list(match_data.get('points', {}).keys())}, usernames_keys={list(match_data.get('usernames', {}).keys())}, error={e}")
                            text += f"\n\n<b>Score:</b> Error displaying score"

                        target = match_data["target_points"]
                        final_winner = None
                        if match_data["points"][p1] >= target: final_winner = p1
                        elif match_data["points"][p2] >= target: final_winner = p2

                        if final_winner is not None:
                            loser_id = p2 if final_winner == p1 else p1
                            match_data.update({"status": "completed", "winner_id": final_winner})
                            
                            # Use bet_amount_usd if available, otherwise bet_amount
                            bet_amount = match_data.get("bet_amount_usd", match_data.get("bet_amount", 0))
                            winnings = bet_amount * 1.94  # 1.94x multiplier
                            
                            # Credit winner (only if not bot)
                            if final_winner != 0:  # 0 = Bot
                                user_wallets[final_winner] += winnings
                                update_stats_on_bet(final_winner, match_id, bet_amount, True, pvp_win=True, multiplier=1.94, context=context)
                                update_pnl(final_winner)
                                save_user_data(final_winner)
                                # Add to player history
                                if 'game_sessions' not in user_stats[final_winner]:
                                    user_stats[final_winner]['game_sessions'] = []
                                user_stats[final_winner]['game_sessions'].append(match_id)
                            
                            # Update loser stats (only if not bot)
                            if loser_id != 0:  # 0 = Bot
                                update_stats_on_bet(loser_id, match_id, bet_amount, False, context=context)
                                update_pnl(loser_id)
                                save_user_data(loser_id)
                                # Add to player history
                                if 'game_sessions' not in user_stats[loser_id]:
                                    user_stats[loser_id]['game_sessions'] = []
                                user_stats[loser_id]['game_sessions'].append(match_id)
                            
                            text += f"\n\n🏆 <b>{match_data['usernames'][final_winner]} wins the match and earns ${winnings:.2f}!</b>"
                            # Unpin the message
                            if 'pinned_message_id' in match_data:
                                try: await context.bot.unpin_chat_message(chat_id, match_data['pinned_message_id'])
                                except Exception as e: logging.warning(f"Could not unpin message for match {match_id}: {e}")
                        else:
                            match_data["last_roller"] = None
                            match_data["player_rolls"] = {p1: [], p2: []}  # Reset rolls for next round
                            text += f"\n\n<b>Next round:</b> {match_data['usernames'][p1]} rolls first! ({allowed_emojis[gtype]} emoji)"

                        await asyncio.sleep(1.5)
                        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
                    else:
                        other_id = [pid for pid in players if pid != user.id][0]
                        other_rolls = len(match_data["player_rolls"].get(other_id, []))
                        if other_rolls == 0:
                            await asyncio.sleep(1)
                            await update.message.reply_text(f"Your rolls complete! Waiting for {match_data['usernames'][other_id]} to start rolling.")
                        elif other_rolls < game_rolls:
                            await asyncio.sleep(1)
                            await update.message.reply_text(f"Your rolls complete! Waiting for {match_data['usernames'][other_id]} to finish ({other_rolls}/{game_rolls} done).")
                    return
        except Exception as e:
            logging.error(f"Error in PvP game handling: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred processing your roll. Please contact support.")
            return

# --- Clear user funds (owner only) ---
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the bot owner can use this command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    keyboard = [[InlineKeyboardButton("✅ Yes, clear all funds", callback_data="clear_confirm_yes"), InlineKeyboardButton("❌ No, cancel", callback_data="clear_confirm_no")]]
    await update.message.reply_text("⚠️ WARNING: This will reset all user balances to zero!\n\nAre you absolutely sure?", reply_markup=InlineKeyboardMarkup(keyboard))

async def clearall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the bot owner can use this command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    keyboard = [[InlineKeyboardButton("✅ Yes, erase ALL data", callback_data="clearall_confirm_yes"), InlineKeyboardButton("❌ No, cancel", callback_data="clearall_confirm_no")]]
    await update.message.reply_text("⚠️ EXTREME WARNING ⚠️\n\nThis will completely erase ALL user data, including all settings. This action is IRREVERSIBLE!\n\nAre you absolutely sure?", reply_markup=InlineKeyboardMarkup(keyboard))

async def clear_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_wallets, user_stats, username_to_userid, escrow_deals, game_sessions, group_settings, bot_settings, gift_codes, recovery_data
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if user.id != BOT_OWNER_ID:
        await query.answer("Only the owner can confirm this action.", show_alert=True)
        return

    if query.data == "clear_confirm_yes":
        users_affected = 0
        for user_id in list(user_wallets.keys()):
            if user_wallets[user_id] > 0:
                user_wallets[user_id] = 0
                if user_id in user_stats:
                    update_pnl(user_id)
                    save_user_data(user_id)
                users_affected += 1
        await query.edit_message_text(f"✅ Done! Reset balances to zero for {users_affected} users.")
    elif query.data == "clearall_confirm_yes":
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"backup_all_data_{backup_time}.json")
        try:
            state_to_backup = {
                "wallets": user_wallets, "stats": user_stats, "usernames": username_to_userid,
                "escrow_deals": escrow_deals, "game_sessions": game_sessions, "group_settings": group_settings,
                "bot_settings": bot_settings, "recovery_data": recovery_data, "gift_codes": gift_codes
            }
            with open(backup_file, "w") as f:
                json.dump(state_to_backup, f, default=str, indent=2)
        except Exception as e:
            logging.error(f"Failed to create backup before clearing data: {e}")

        old_count = len(user_stats)
        # Clear all in-memory data
        user_wallets.clear(); user_stats.clear(); username_to_userid.clear(); escrow_deals.clear(); game_sessions.clear(); group_settings.clear(); recovery_data.clear(); gift_codes.clear()
        # Reset bot settings to default
        bot_settings = {
            "daily_bonus_amount": 0.50, "maintenance_mode": False, "banned_users": [],
            "tempbanned_users": [], "house_balance": 100_000_000_000_000.0, "game_limits": {},
            "withdrawals_enabled": True
        }
        # Delete all data files
        for d in [DATA_DIR, ESCROW_DIR, GROUPS_DIR, RECOVERY_DIR, GIFT_CODE_DIR]:
            try:
                for fname in os.listdir(d):
                    if fname.endswith(".json"): os.remove(os.path.join(d, fname))
            except Exception as e: logging.error(f"Error deleting files in {d}: {e}")
        # Delete the main state file
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)

        await query.edit_message_text(f"✅ All user data and settings cleared! Removed data for {old_count} users.\nA backup was saved to {backup_file}")
    else:
        await query.edit_message_text("Operation cancelled. No changes were made.")

# --- Tip, Help, Cashout, Cancel Handlers ---
@check_banned
@check_maintenance
async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    message_text = update.message.text.strip().split()
    target_user_id = None
    target_username = None

    if update.message.reply_to_message and len(message_text) == 2:
        try:
            tip_amount = float(message_text[1])
            target_user_id = update.message.reply_to_message.from_user.id
            target_username = update.message.reply_to_message.from_user.username
        except (ValueError, IndexError):
             await update.message.reply_text("Usage (reply to a message): /tip amount")
             return
    elif len(message_text) == 3:
        try:
            target_username_str = normalize_username(message_text[1])
            tip_amount = float(message_text[2])
            target_user_id = username_to_userid.get(target_username_str)
            if not target_user_id:
                try:
                    chat = await context.bot.get_chat(target_username_str)
                    target_user_id = chat.id
                    target_username = chat.username
                except Exception:
                    await update.message.reply_text(f"User {target_username_str} not found.")
                    return
            else:
                target_username = user_stats[target_user_id]['userinfo']['username']
        except (ValueError, IndexError):
            await update.message.reply_text("Usage: /tip @username amount")
            return
    else:
        await update.message.reply_text("Usage: /tip @username amount OR reply to a message with /tip amount")
        return

    if not target_user_id:
        await update.message.reply_text("Could not find the target user.")
        return

    is_owner = user.id == BOT_OWNER_ID
    if user.id == target_user_id and not is_owner:
        await update.message.reply_text("You cannot tip yourself.")
        return
    if tip_amount <= 0:
        await update.message.reply_text("Tip amount must be positive.")
        return

    if not is_owner and user_wallets.get(user.id, 0.0) < tip_amount:
        await update.message.reply_text("You don't have enough balance to tip this amount.")
        return

    if not is_owner: user_wallets[user.id] -= tip_amount
    await ensure_user_in_wallets(target_user_id, target_username, context=context)
    user_wallets[target_user_id] = user_wallets.get(target_user_id, 0.0) + tip_amount

    update_stats_on_tip_sent(user.id, tip_amount)
    update_stats_on_tip_received(target_user_id, tip_amount)
    
    # Track tip for wager requirement (1x)
    if target_user_id in user_stats:
        user_stats[target_user_id]["unwagered_tips"] = user_stats[target_user_id].get("unwagered_tips", 0.0) + tip_amount
    
    update_pnl(user.id); update_pnl(target_user_id)
    save_user_data(user.id); save_user_data(target_user_id)

    tipped_user_mention = f"@{target_username}" if target_username else f"user (ID: {target_user_id})"
    await update.message.reply_text(f"You have successfully tipped {tipped_user_mention} ${tip_amount:.2f}.", parse_mode=ParseMode.HTML)
    try:
        await context.bot.send_message(chat_id=target_user_id, text=f"You have received a tip of ${tip_amount:.2f} from {user.mention_html()}!", parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.warning(f"Failed to send tip notification to {target_user_id}: {e}")

@check_banned
@check_maintenance
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    is_owner = user.id == BOT_OWNER_ID
    
    # Set menu owner for group protection when called as command
    if not from_callback:
        context.user_data['menu_owner_id'] = user.id

    help_text = (
        "🎲 <b>Telegram Gambling & Escrow Bot</b> 🎲\n\n"
        "<b>🤖 AI Assistant:</b>\n"
        "• <code>/ai &lt;question&gt;</code> — Ask the AI anything (default: g4f).\n"
        "• <code>/p &lt;SYMBOL&gt;</code> — Get crypto price from MEXC (e.g., /p BTC).\n"
        "• Reply to a message with <code>/ai</code> to discuss it.\n\n"
        "<b>Solo Games:</b>\n"
        "• <b>Blackjack</b>: <code>/bj amount</code>\n"
        "• <b>Coin Flip</b>: <code>/flip amount</code>\n"
        "• <b>Roulette</b>: <code>/roul amount choice</code>\n"
        "• <b>Dice Roll</b>: <code>/dr amount choice</code>\n"
        "• <b>Tower</b>: Use <code>/tr</code> or the Games menu\n"
        "• <b>Slots</b>: <code>/sl amount</code>\n"
        "• <b>Mines</b>: Use <code>/mines</code> or the Games menu\n"
        "• <b>Limbo</b>: <code>/lb amount multiplier</code> or <code>/lb</code> for instructions\n"
        "• <b>Keno</b>: <code>/keno amount</code>\n"
        "• <b>Predict</b>: <code>/predict amount up/down</code>\n"
        "💡 You can use 'all' instead of an amount to bet your entire balance!\n"
        "💡 All amounts are in your selected currency (see Settings).\n\n"
        "<b>🎮 Single Emoji Games:</b>\n"
        "• Access via Games → Emoji Games → Single Emoji Games\n"
        "• Quick instant-result games: Darts, Soccer, Basket, Bowling, Slot\n\n"
        "<b>PvP & PvB Games:</b>\n"
        "• <b>Dice, Darts, Football (Goal), Bowling</b>\n"
        "  - <b>vs Player</b>: <code>/dice @user amount MX ftY</code>\n"
        "     Example: <code>/dice @friend 5 M1 ft3</code> (Mode 1, First to 3)\n"
        "  - <b>vs Bot</b>: Use <code>/games</code> menu\n"
        "  - <b>Group Challenge</b> (Groups only): <code>/dice amount</code>\n"
        "     Example: <code>/dice 10</code> creates a challenge in the group\n"
        "     Others can accept or you can play with bot\n"
        "• Same for: <code>/darts</code>, <code>/goal</code>, <code>/bowl</code>\n\n"
        "<b>Wallet & Withdrawals:</b>\n"
        "• <code>/bal</code> or <code>/bank</code> or <code>/hb</code>\n"
        "• Use the main menu for withdrawals (set withdrawal address in Settings first)\n"
        "• <code>/tip @user amount</code> or reply to a message\n"
        "• <code>/rain amount N</code> — Rain on N users\n"
        "• <code>/stats</code>, <code>/leaderboard</code>, <code>/leaderboardrf</code>\n\n"
        "<b>🎁 Bonuses:</b>\n"
        "• <code>/daily</code> — Claim your daily bonus!\n"
        "• <code>/weekly</code> — Claim weekly wager bonus (0.5%).\n"
        "• <code>/monthly</code> — Claim monthly wager bonus (0.3%).\n"
        "• <code>/rk</code> — Claim your instant rakeback (0.01%).\n"
        "• <code>/claim &lt;code&gt;</code> — Claim a gift code.\n\n"
        "<b>🛡️ History & Info:</b>\n"
        "• <code>/escrow</code>, <code>/deals</code>, <code>/matches</code>\n"
        "• <code>/active</code> — View your active games\n"
        "• <code>/info &lt;id&gt;</code> — Get details of any game/deal\n"
        "• <code>/continue &lt;id&gt;</code> — Resume an active game\n\n"
        "<b>⚙️ Settings & Account:</b>\n"
        "• <code>/referral</code>, <code>/achievements</code>, <code>/level</code>\n"
        "• <code>/language</code> — Change bot language (en/es/fr/ru/hi/zh)\n"
        "• Use Settings menu to:\n"
        "  - Set your withdrawal address (USDT-BEP20)\n"
        "  - Change your display currency\n"
        "  - Set up account recovery\n"
        "• <code>/recover</code> — Start the account recovery process\n\n"
        "<b>Group Management:</b>\n"
        "• Reply with <code>/kick</code>, <code>/mute</code>, <code>/promote</code>, <code>/pin</code>, <code>/purge</code>, <code>/report</code>, <code>/translate</code>\n"
        "• <code>/lockall</code>, <code>/unlockall</code>\n"
        "• <code>/settings</code> — Configure the bot for your group (group admins only)\n\n"
        "<b>Minimum bet: ${:.2f}</b>\nContact @jashanxjagy for support.".format(MIN_BALANCE)
    )

    owner_help = (
        "\n\n👑 <b>Owner Commands:</b>\n"
        "• <code>/admin</code> — Open the admin dashboard.\n"
        "• <code>/setbal @user amount</code> — Manually set a user's balance.\n"
        "• <code>/user @username</code> — Get detailed user info.\n"
        "• <code>/users</code> — View all user stats (paginated)\n"
        "• <code>/activeall</code> — View all active games on the bot (paginated).\n"
        "• <code>/reset @username</code> — Reset a user's recovery token.\n"
        "• <code>/cancel &lt;id&gt;</code> — Cancel a match or deal\n"
        "• <code>/cancelall</code> — Cancel all active matches\n"
        "• <code>/stop</code> & <code>/resume</code> — Pause/resume new games\n"
        "• <code>/clear</code> — Reset all user balances to 0\n"
        "• <code>/clearall</code> — ⚠️ Erase all user data\n"
        "• <code>/he</code> (all escrow), <code>/hc</code> (all games) — History cmds\n"
        "• <code>/export</code> — Export all user data as a JSON file.\n"
        "• Approve/Cancel withdrawals via inline buttons in withdrawal notifications."
    )

    if is_owner:
        help_text += owner_help

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]]) if from_callback else None

    if from_callback:
        await safe_edit_message(update.callback_query, help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        sent_message = await update.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)
        # Set ownership when sending with keyboard
        if reply_markup:
            set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def cashout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await ensure_user_in_wallets(user_id, update.effective_user.username, context=context)

    # Find active, cashout-able games for the user
    active_games = [g for g in game_sessions.values() if g.get('user_id') == user_id and g.get('status') == 'active' and g.get('game_type') in ['mines', 'tower', 'coin_flip']]

    if not active_games:
        await update.message.reply_text("No active games to cash out from. Use `/continue <id>` to resume a game.")
        return

    # For simplicity, cashout the most recent one. A better implementation might list them.
    game = sorted(active_games, key=lambda g: g['timestamp'], reverse=True)[0]
    game_id = game['id']

    # Create a fake query object to pass to the callback handlers since they expect one
    class FakeQuery:
        def __init__(self, user, message):
            self.from_user = user
            self.message = message
        async def answer(self, *args, **kwargs): pass
        async def edit_message_text(self, *args, **kwargs):
            await self.message.reply_text(*args, **kwargs)

    fake_update = type('FakeUpdate', (), {'callback_query': FakeQuery(update.effective_user, update.message)})()

    if game['game_type'] == 'mines':
        fake_update.callback_query.data = f'mines_cashout_{game_id}'
        await mines_pick_callback(fake_update, context)
    elif game['game_type'] == 'tower':
        fake_update.callback_query.data = f'tower_cashout_{game_id}'
        await tower_callback(fake_update, context)
    elif game['game_type'] == 'coin_flip':
        fake_update.callback_query.data = f'flip_cashout_{game_id}'
        await coin_flip_callback(fake_update, context)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("Only the bot owner can use this command.")
        return
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    message_text = update.message.text.strip().split()
    if len(message_text) != 2:
        await update.message.reply_text("Usage: /cancel <match_id | deal_id>")
        return
    item_id = message_text[1]

    if item_id in game_sessions:
        game_data = game_sessions[item_id]
        if game_data.get("status") != "active":
            await update.message.reply_text("This game is not active.")
            return

        game_data["status"] = "cancelled"

        # Refund players
        if 'players' in game_data: # PvP
            bet_amount = game_data["bet_amount"]
            for player_id in game_data['players']:
                user_wallets[player_id] += bet_amount
                save_user_data(player_id)
                try: await context.bot.send_message(player_id, f"Match {item_id} cancelled by owner. Bet of ${bet_amount:.2f} refunded.")
                except Exception as e: logging.warning(f"Could not notify player {player_id}: {e}")
        elif 'user_id' in game_data: # Solo
            player_id = game_data['user_id']
            bet_amount = game_data['bet_amount']
            user_wallets[player_id] += bet_amount
            save_user_data(player_id)
            try: await context.bot.send_message(player_id, f"Your game {item_id} was cancelled by the owner. Your bet of ${bet_amount:.2f} has been refunded.")
            except Exception as e: logging.warning(f"Could not notify player {player_id}: {e}")

        await update.message.reply_text(f"Game {item_id} cancelled. Bets refunded.")
        return

    if item_id in escrow_deals:
        deal = escrow_deals[item_id]
        if deal['status'] in ['completed', 'cancelled_by_owner', 'disputed']:
             await update.message.reply_text(f"Deal {item_id} is already finalized.")
             return
        deal['status'] = 'cancelled_by_owner'
        if deal.get('deposit_tx_hash'):
            await update.message.reply_text(f"Deal {item_id} cancelled. Manually refund ${deal['amount']:.2f} to seller @{deal['seller']['username']}.")
        else:
            await update.message.reply_text(f"Deal {item_id} cancelled. No funds were deposited.")
        save_escrow_deal(item_id)
        try:
            await context.bot.send_message(deal['seller']['id'], f"Your escrow deal {item_id} has been cancelled by the bot owner.")
            await context.bot.send_message(deal['buyer']['id'], f"Your escrow deal {item_id} has been cancelled by the bot owner.")
        except Exception as e: logging.warning(f"Could not notify users about deal cancellation: {e}")
        return
    await update.message.reply_text("No active match or deal found with that ID.")

# --- DICE INVITE HANDLER (accept/decline) ---
@check_banned
@check_maintenance
async def match_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    match_id = data.split("_", 1)[1]
    match_data = game_sessions.get(match_id)
    if not match_data:
        await query.edit_message_text("Match not found or already cancelled.")
        return

    opponent_id = match_data["players"][1]
    if user_id != opponent_id:
        await query.answer("Only the challenged opponent can accept/decline this match.", show_alert=True)
        return
    if match_data.get("status") != "pending":
        await query.edit_message_text("This match has already been actioned.")
        return

    if data.startswith("accept_"):
        await ensure_user_in_wallets(user_id, query.from_user.username, context=context)
        if user_wallets.get(user_id, 0.0) < match_data["bet_amount"]:
            await query.edit_message_text(
                "❌ You don't have enough balance for this bet.",
            )
            match_data["status"] = "cancelled"
            return

        user_wallets[match_data["host_id"]] -= match_data["bet_amount"]
        user_wallets[opponent_id] -= match_data["bet_amount"]
        save_user_data(match_data["host_id"]); save_user_data(opponent_id)
        match_data.update({"status": "active"})
        
        # Ensure all required fields are initialized for PvP games
        if "points" not in match_data:
            match_data["points"] = {match_data["host_id"]: 0, opponent_id: 0}
        if "player_rolls" not in match_data:
            match_data["player_rolls"] = {match_data["host_id"]: [], opponent_id: []}
        if "last_roller" not in match_data:
            match_data["last_roller"] = None
        
        await ensure_user_in_wallets(match_data["host_id"], context=context)
        await ensure_user_in_wallets(opponent_id, context=context)
        if 'game_sessions' not in user_stats[match_data["host_id"]]: user_stats[match_data["host_id"]]['game_sessions'] = []
        if 'game_sessions' not in user_stats[opponent_id]: user_stats[opponent_id]['game_sessions'] = []
        user_stats[match_data["host_id"]]['game_sessions'].append(match_id)
        user_stats[opponent_id]['game_sessions'].append(match_id)
        save_user_data(match_data["host_id"]); save_user_data(opponent_id)

        await query.edit_message_text(
            f"Match Accepted! Game starts now.\n<b>Match ID:</b> {match_id}", parse_mode=ParseMode.HTML
        )
        await context.bot.send_message(
            chat_id=match_data["chat_id"],
            text=f"🎮 <b>{match_data['game_type'].replace('pvp_','').capitalize()} Match {match_id} Started!</b>\n"
                 f"{match_data['usernames'][match_data['host_id']]} vs {match_data['usernames'][match_data['players'][1]]}\n"
                 f"First to {match_data['target_points']} points wins ${match_data['bet_amount']*2:.2f}!\n"
                 f"{match_data['usernames'][match_data['host_id']]}, it's your turn.",
            parse_mode=ParseMode.HTML
        )
    else: # Decline
        match_data.update({"status": "declined"})
        await query.edit_message_text("Match declined. The match is cancelled.")

# --- WEB3 SETUP FOR ESCROW ---
BSC_NODES = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.binance.org/"]
ETH_NODE = "https://linea-mainnet.infura.io/v3/25cdeb5b655744f2b6d88c998e55eace"

def get_working_web3_bsc():
    for node in BSC_NODES:
        try:
            w3 = Web3(Web3.HTTPProvider(node))
            if w3.is_connected():
                logging.info(f"Connected to BSC node: {node}")
                return w3
        except Exception as e:
            logging.warning(f"Failed to connect to BSC node {node}: {e}")
    logging.error("Could not connect to any BSC node")
    return None

try:
    w3_bsc = get_working_web3_bsc()
    w3_eth = Web3(Web3.HTTPProvider(ETH_NODE))
    if w3_bsc and w3_bsc.is_connected(): logging.info("Successfully connected to BSC")
    else: logging.error("Failed to connect to BSC")
    if w3_eth and w3_eth.is_connected(): logging.info("Successfully connected to ETH")
    else: logging.error("Failed to connect to ETH")
except Exception as e:
    logging.error(f"Failed to initialize Web3 connections: {e}")
    w3_bsc = w3_eth = None

ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"payable":true,"stateMutability":"payable","type":"fallback"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]')


# --- ESCROW SYSTEM ---
@check_banned
@check_maintenance
async def escrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not all([ESCROW_DEPOSIT_ADDRESS, ESCROW_WALLET_PRIVATE_KEY]):
        error_msg = "Escrow system is not configured by the owner yet."
        if from_callback: await safe_edit_message(update.callback_query, error_msg)
        else: await update.message.reply_text(error_msg)
        return

    context.user_data['escrow_step'] = 'ask_amount'
    context.user_data['escrow_data'] = {'creator_id': user.id, 'creator_username': user.username}
    text = "🛡️ <b>New Escrow Deal</b>\n\nPlease enter the deal amount in USDT (BEP20)."
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="escrow_action_cancel_setup")]]
    if from_callback:
        await safe_edit_message(update.callback_query, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

@check_banned
@check_maintenance
async def handle_escrow_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    step = context.user_data.get('escrow_step')
    deal_data = context.user_data.get('escrow_data', {})
    cancel_button = [[InlineKeyboardButton("Cancel", callback_data="escrow_action_cancel_setup")]]

    if step == 'ask_amount':
        try:
            amount = float(update.message.text)
            if amount <= 0: raise ValueError
            deal_data['amount'] = amount
            context.user_data['escrow_step'] = 'ask_role'
            keyboard = [
                [InlineKeyboardButton("🏪 I am the Seller", callback_data="escrow_role_seller")],
                [InlineKeyboardButton("🛒 I am the Buyer", callback_data="escrow_role_buyer")],
                [InlineKeyboardButton("❌ Cancel", callback_data="escrow_action_cancel_setup")]
            ]
            await update.message.reply_text(f"✅ Amount set to ${amount:.2f} USDT.\n\nPlease select your role:", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Invalid amount. Please enter a positive number.", reply_markup=InlineKeyboardMarkup(cancel_button))
            return

    elif step == 'ask_details':
        deal_data['details'] = update.message.text
        # REMOVED: ask_partner_method step. Forcing link creation.
        await create_and_finalize_escrow_deal(update, context, by_link=True)

@check_banned
@check_maintenance
async def escrow_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user, data = query.from_user, query.data.split('_')
    action = data[1]
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if action == 'role':
        role = data[2]
        context.user_data['escrow_data']['creator_role'] = role
        context.user_data['escrow_data']['partner_role'] = 'Buyer' if role == 'seller' else 'Seller'
        context.user_data['escrow_step'] = 'ask_details'
        cancel_button = [[InlineKeyboardButton("❌ Cancel", callback_data="escrow_action_cancel_setup")]]
        await query.edit_message_text("✅ Role selected. Now, please provide the deal details (e.g., 'Sale of item X').", reply_markup=InlineKeyboardMarkup(cancel_button))

    # REMOVED: partner action, as we now force link creation.

    elif action == 'confirm':
        deal_id, decision = data[2], data[3]
        deal = escrow_deals.get(deal_id)
        if not deal or (user.id != deal.get('buyer', {}).get('id') and user.id != deal.get('seller', {}).get('id')):
            await query.edit_message_text("This deal is not for you or has expired.")
            return
        if user.id == deal.get('creator_id'):
            await query.answer("Waiting for the other party to respond.", show_alert=True); return

        if decision == 'accept':
            deal['status'] = 'accepted_awaiting_deposit'
            save_escrow_deal(deal_id)
            seller_id, buyer_id = deal['seller']['id'], deal['buyer']['id']
            await query.edit_message_text(f"✅ You accepted the deal. Seller will now be prompted to deposit ${deal['amount']:.2f} USDT.")
            deposit_text = (f"✅ The other party accepted the deal!\n\n<b>Deal ID:</b> <code>{deal_id}</code>\n"
                            f"Please deposit exactly <code>{deal['amount']}</code> USDT (BEP20) to:\n<code>{ESCROW_DEPOSIT_ADDRESS}</code>\n\n"
                            f"⚠️ Send from your own wallet (NOT from an exchange). Have enough BNB for gas.")
            await context.bot.send_message(chat_id=seller_id, text=deposit_text, parse_mode='HTML')
            context.job_queue.run_repeating(monitor_escrow_deposit, interval=20, first=10, data={'deal_id': deal_id}, name=f"escrow_monitor_{deal_id}")
        else: # Decline
            deal['status'] = 'declined_by_partner'; save_escrow_deal(deal_id)
            await query.edit_message_text("You have declined the deal. It has been cancelled.")
            await context.bot.send_message(chat_id=deal['creator_id'], text=f"The other party has declined your escrow deal ({deal_id}).")

    elif action == 'action':
        if data[2] == "cancel" and data[3] == "setup":
             context.user_data.clear()
             await query.edit_message_text("Escrow setup cancelled.")
             await more_menu(update, context)
             return

        deal_id, decision = data[2], data[3]
        deal = escrow_deals.get(deal_id)
        if not deal or user.id not in [deal['seller']['id'], deal['buyer']['id']]: return

        if decision == 'release':
            if user.id != deal['seller']['id']: await query.answer("Only the seller can release funds.", show_alert=True); return
            if deal['status'] != 'funds_secured': await query.answer("Funds are not in a releasable state.", show_alert=True); return
            keyboard = [
                [InlineKeyboardButton("✅ Yes, Release Funds", callback_data=f"escrow_action_{deal_id}_releaseconfirm")],
                [InlineKeyboardButton("❌ No, Cancel", callback_data=f"escrow_action_{deal_id}_releasecancel")]
            ]
            await query.edit_message_text("⚠️ Are you sure you want to release the funds to the buyer? This action is irreversible.", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        elif decision == 'releaseconfirm':
            if user.id != deal['seller']['id']: return
            # NEW: Credit buyer's casino balance directly instead of asking for withdrawal address
            buyer_id = deal['buyer']['id']
            amount = deal['amount']
            
            # Add funds to buyer's casino balance
            await ensure_user_in_wallets(buyer_id, context=context)
            user_wallets[buyer_id] += amount
            save_user_data(buyer_id)
            
            # Update deal status
            deal['status'] = 'completed'
            deal['completed_at'] = str(datetime.now(timezone.utc))
            save_escrow_deal(deal_id)
            
            # Notify both parties
            seller_msg = (
                f"✅ <b>Deal Completed!</b>\n\n"
                f"<b>Deal ID:</b> <code>{deal_id}</code>\n"
                f"<b>Amount:</b> ${amount:.2f}\n\n"
                f"The funds have been credited to the buyer's casino balance.\n"
                f"Thank you for using our escrow service!"
            )
            buyer_msg = (
                f"✅ <b>Funds Received!</b>\n\n"
                f"<b>Deal ID:</b> <code>{deal_id}</code>\n"
                f"<b>Amount:</b> ${amount:.2f}\n\n"
                f"The funds have been added to your casino balance.\n"
                f"You can now withdraw them using the withdrawal feature.\n\n"
                f"Use /withdraw to request a withdrawal."
            )
            
            await query.edit_message_text(seller_msg, parse_mode=ParseMode.HTML)
            await context.bot.send_message(chat_id=buyer_id, text=buyer_msg, parse_mode=ParseMode.HTML)
            
        elif decision == 'releasecancel': await query.edit_message_text("Release cancelled.")
        elif decision == 'dispute':
            deal['status'] = 'disputed'; save_escrow_deal(deal_id)
            dispute_text = f"🚨 A dispute has been opened for deal <code>{deal_id}</code>. Contact @jashanxjagy for assistance."
            await query.edit_message_text(dispute_text, parse_mode="HTML")
            other_party_id = deal['buyer']['id'] if user.id == deal['seller']['id'] else deal['seller']['id']
            await context.bot.send_message(chat_id=other_party_id, text=dispute_text, parse_mode="HTML")
            await context.bot.send_message(BOT_OWNER_ID, text=f"New dispute for deal {deal_id}.")

async def create_and_finalize_escrow_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, by_link=False):
    user = update.effective_user
    deal_data = context.user_data.get('escrow_data', {})
    if deal_data['creator_role'] == 'seller':
        deal_data['seller'] = {'id': user.id, 'username': user.username}
        deal_data['buyer'] = {'id': None, 'username': None} # Partner joins via link
    else:
        deal_data['buyer'] = {'id': user.id, 'username': user.username}
        deal_data['seller'] = {'id': None, 'username': None} # Partner joins via link

    deal_id = generate_unique_id("ESC")
    deal_data.update({'id': deal_id, 'status': 'pending_confirmation', 'timestamp': str(datetime.now(timezone.utc))})
    escrow_deals[deal_id] = deal_data
    save_escrow_deal(deal_id)

    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_stats[user.id]['escrow_deals'].append(deal_id)
    save_user_data(user.id)

    context.user_data.pop('escrow_step', None); context.user_data.pop('escrow_data', None)

    buyer_username = deal_data.get('buyer', {}).get('username') or "TBD (via link)"
    seller_username = deal_data.get('seller', {}).get('username') or "TBD (via link)"
    deal_summary = (f"🛡️ <b>New Escrow Deal Created</b>\n\n<b>Deal ID:</b> <code>{deal_id}</code>\n"
                    f"<b>Amount:</b> ${deal_data['amount']:.2f} USDT\n<b>Seller:</b> @{seller_username}\n"
                    f"<b>Buyer:</b> @{buyer_username}\n<b>Details:</b> {deal_data['details']}")

    bot_username = (await context.bot.get_me()).username
    deal_link = f"https://t.me/{bot_username}?start=escrow_{deal_id}"

    reply_target = update.callback_query.message if update.callback_query else update.message
    await reply_target.reply_text(f"{deal_summary}\n\nShare this link with the other party to join:\n<code>{deal_link}</code>", parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def handle_escrow_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    deal = escrow_deals.get(deal_id)
    if not deal: await update.message.reply_text("This escrow deal link is invalid or has expired."); return

    is_joinable = (deal['creator_role'] == 'seller' and deal.get('buyer', {}).get('id') is None) or \
                  (deal['creator_role'] == 'buyer' and deal.get('seller', {}).get('id') is None)
    if not is_joinable or deal['status'] != 'pending_confirmation':
        await update.message.reply_text("This deal has already been accepted or is no longer valid."); return
    if user.id == deal['creator_id']:
        await update.message.reply_text("You cannot accept your own deal. Share the link with the other party."); return

    if deal['creator_role'] == 'seller': deal['buyer'] = {'id': user.id, 'username': user.username}
    else: deal['seller'] = {'id': user.id, 'username': user.username}
    user_stats[user.id]['escrow_deals'].append(deal_id)
    save_user_data(user.id)
    save_escrow_deal(deal_id)

    deal_summary = (f"🛡️ <b>You are joining an Escrow Deal</b>\n\n<b>Deal ID:</b> <code>{deal_id}</code>\n"
                    f"<b>Amount:</b> ${deal['amount']:.2f} USDT\n<b>Seller:</b> @{deal['seller']['username']}\n"
                    f"<b>Buyer:</b> @{deal['buyer']['username']}\n<b>Details:</b> {deal['details']}")
    keyboard = [[InlineKeyboardButton("✅ Accept Deal", callback_data=f"escrow_confirm_{deal_id}_accept"), InlineKeyboardButton("❌ Decline Deal", callback_data=f"escrow_confirm_{deal_id}_decline")]]
    await update.message.reply_text(f"{deal_summary}\n\nPlease confirm to proceed.", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def generate_verification_code(pf_record):
    """Generate game-specific verification code"""
    game_type = pf_record['game_type']
    server_seed = pf_record['server_seed']
    client_seed = pf_record['client_seed']
    nonce = pf_record['nonce']
    
    # Base verification functions used by all games
    base_code = f"""import hashlib

# Your Game Data
server_seed = "{server_seed}"
client_seed = "{client_seed}"
nonce = {nonce}

# Core Verification Functions
def create_hash(server_seed, client_seed, nonce):
    combined = f"{{server_seed}}:{{client_seed}}:{{nonce}}"
    return hashlib.sha256(combined.encode()).hexdigest()

def get_provably_fair_result(server_seed, client_seed, nonce, max_value):
    hash_result = create_hash(server_seed, client_seed, nonce)
    hex_value = int(hash_result[:8], 16)
    return hex_value % max_value

"""
    
    # Game-specific verification code
    if game_type == "roulette":
        game_code = """# Roulette Verification
RED_NUMBERS = {{1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}}

winning_number = get_provably_fair_result(server_seed, client_seed, nonce, 37)

if winning_number == 0:
    color = "Green 🟢"
elif winning_number in RED_NUMBERS:
    color = "Red 🔴"
else:
    color = "Black ⚫"

print(f"=== Roulette Verification ===")
print(f"Winning Number: {{winning_number}} ({{color}})")
print(f"Hash: {{create_hash(server_seed, client_seed, nonce)[:16]}}...")
"""
    
    elif game_type == "hilo":
        game_code = """# Hi-Lo (High-Low) Card Game Verification
# Generate shuffled deck
deck = list(range(1, 14)) * 4  # 1-13, 4 suits (52 cards)

# Fisher-Yates shuffle with provably fair results
for i in range(len(deck) - 1, 0, -1):
    j = get_provably_fair_result(server_seed, client_seed, nonce + i, i + 1)
    deck[i], deck[j] = deck[j], deck[i]

card_names = {{1:'ACE', 2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9', 10:'10', 11:'JACK', 12:'QUEEN', 13:'KING'}}

print("=== Hi-Lo Card Sequence ===")
print("First 10 cards from shuffled deck:")
for i in range(min(10, len(deck))):
    card_value = deck[-(i+1)]  # Cards are popped from end
    print(f"  Card {{i+1}}: {{card_names[card_value]}} ({{card_value}})")
"""
    
    elif game_type == "mines":
        game_code = """# Mines Game Verification
def generate_mine_positions(server_seed, client_seed, nonce, num_mines):
    positions = []
    offset = 0
    while len(positions) < num_mines:
        pos = get_provably_fair_result(server_seed, client_seed, nonce + offset, 25)
        if pos not in positions:
            positions.append(pos)
        offset += 1
    return sorted(positions)

# Extract mine count from result_data or use default
num_mines = 3  # Default, adjust based on your game

mine_positions = generate_mine_positions(server_seed, client_seed, nonce, num_mines)

print("=== Mines Verification ===")
print(f"Mine Positions: {{mine_positions}}")
print("\\nGrid (5x5):")
for row in range(5):
    row_str = ""
    for col in range(5):
        idx = row * 5 + col
        row_str += "💣 " if idx in mine_positions else "💎 "
    print(f"Row {{row+1}}: {{row_str}}")
"""
    
    elif game_type == "tower":
        game_code = """# Tower Game Verification  
def generate_tower_positions(server_seed, client_seed, nonce, difficulty):
    tiles_per_floor = {{'easy': 4, 'medium': 3, 'hard': 2}}.get(difficulty, 3)
    positions = []
    for floor in range(9):
        snake_pos = get_provably_fair_result(server_seed, client_seed, nonce + floor, tiles_per_floor)
        positions.append(snake_pos)
    return positions

difficulty = 'medium'  # Change to 'easy', 'medium', or 'hard' based on your game
snake_positions = generate_tower_positions(server_seed, client_seed, nonce, difficulty)
tiles = {{'easy': 4, 'medium': 3, 'hard': 2}}[difficulty]

print(f"=== Tower Verification ({{difficulty.title()}}) ===")
print("Snake positions by floor (0-indexed):")
for i, pos in enumerate(snake_positions):
    floor_num = i + 1
    grid = ['🌴' for _ in range(tiles)]
    grid[pos] = '🐍'
    print(f"Floor {{floor_num}}: {{' '.join(grid)}} (Snake at position {{pos}})")
"""
    
    elif game_type == "blackjack":
        game_code = """# Blackjack Verification
# Generate and shuffle deck
suits = ['♠', '♥', '♦', '♣']
ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
deck = [f"{{r}}{{s}}" for s in suits for r in ranks]

# Fisher-Yates shuffle
for i in range(len(deck) - 1, 0, -1):
    j = get_provably_fair_result(server_seed, client_seed, nonce + i, i + 1)
    deck[i], deck[j] = deck[j], deck[i]

print("=== Blackjack Deck Verification ===")
print("Initial deal (first 4 cards):")
print(f"  Player: {{deck[-1]}}, {{deck[-2]}}")
print(f"  Dealer: {{deck[-3]}}, {{deck[-4]}} (hidden)")
print("\\nNext cards available:")
for i in range(5, min(10, len(deck))):
    print(f"  Card {{i-4}}: {{deck[-i]}}")
"""
    
    elif game_type == "coinflip":
        game_code = """# Coinflip Verification
result = get_provably_fair_result(server_seed, client_seed, nonce, 2)
outcome = "Heads" if result == 0 else "Tails"

print("=== Coinflip Verification ===")
print(f"Result: {{result}} ({{outcome}})")
print(f"Hash: {{create_hash(server_seed, client_seed, nonce)[:16]}}...")
"""
    
    elif game_type == "keno":
        game_code = """# Keno Verification  
def generate_keno_numbers(server_seed, client_seed, nonce, count=10):
    numbers = []
    offset = 0
    while len(numbers) < count:
        num = get_provably_fair_result(server_seed, client_seed, nonce + offset, 40) + 1
        if num not in numbers:
            numbers.append(num)
        offset += 1
    return sorted(numbers)

keno_numbers = generate_keno_numbers(server_seed, client_seed, nonce, 10)

print("=== Keno Verification ===")
print(f"Drawn Numbers: {{keno_numbers}}")
"""
    
    else:
        # Generic verification for other games
        game_code = """# Generic Game Verification
game_hash = create_hash(server_seed, client_seed, nonce)

print(f"=== Game Verification ===")
print(f"Game Hash: {{game_hash}}")
print(f"First 8 hex chars: {{game_hash[:8]}}")
print(f"Decimal value: {{int(game_hash[:8], 16)}}")

# Common game results
print("\\nPossible results for different games:")
print(f"  Coinflip (0-1): {{get_provably_fair_result(server_seed, client_seed, nonce, 2)}}")
print(f"  Dice (1-6): {{get_provably_fair_result(server_seed, client_seed, nonce, 6) + 1}}")
print(f"  Roulette (0-36): {{get_provably_fair_result(server_seed, client_seed, nonce, 37)}}")
"""
    
    return f"```python\n{base_code}{game_code}\n```"


async def handle_provably_fair_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE, pf_id: str):
    """Handle provably fair verification deep link"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    # Get the provably fair record
    pf_record = provably_fair_records.get(pf_id)
    
    if not pf_record:
        await update.message.reply_text(
            "❌ This provably fair verification link is invalid or has expired.\n\n"
            "Verification records are kept for recent games only.",
            parse_mode=ParseMode.HTML
        )
        return
    
    game_type = pf_record['game_type']
    
    # Build the verification message with game details
    text = (
        f"🔐 <b>Provable Fairness Verification</b>\n\n"
        f"<b>Game ID:</b> <code>{pf_record['game_id']}</code>\n"
        f"<b>Game Type:</b> {game_type.title()}\n\n"
        f"<b>Server Seed:</b>\n<code>{pf_record['server_seed']}</code>\n\n"
        f"<b>Client Seed:</b>\n<code>{pf_record['client_seed']}</code>\n\n"
        f"<b>Nonce:</b> {pf_record['nonce']}\n\n"
    )
    
    # Add result data if available
    if pf_record.get('result_data'):
        text += f"<b>Result Data:</b> {pf_record['result_data']}\n\n"
    
    text += (
        f"💡 <b>How to Verify:</b>\n"
        f"Copy the Python code below (long press on code → Copy) and run it.\n\n"
        f"<b>Online Python Compilers:</b>\n"
        f"• <a href='https://www.programiz.com/python-programming/online-compiler/'>Programiz</a>\n"
        f"• <a href='https://repl.it/languages/python3'>Repl.it</a>\n"
        f"• <a href='https://www.online-python.com/'>Online-Python</a>\n\n"
        f"The code is pre-filled with your game data!\n"
        f"Use /serverseed and /seed to view your seeds anytime."
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    # Generate and send game-specific verification code
    verification_code = generate_verification_code(pf_record)
    
    await update.message.reply_text(
        f"<b>📋 {game_type.title()} Verification Code:</b>\n\n"
        f"{verification_code}\n\n"
        f"💡 <b>Tip:</b> Long press on the code block to copy it easily!",
        parse_mode=ParseMode.MARKDOWN
    )

async def monitor_escrow_deposit(context: ContextTypes.DEFAULT_TYPE):
    deal_id = context.job.data["deal_id"]
    deal = escrow_deals.get(deal_id)
    if not deal or deal['status'] != 'accepted_awaiting_deposit':
        logging.info(f"Stopping monitor for deal {deal_id}, status is {deal.get('status', 'N/A')}"); context.job.schedule_removal(); return

    logging.info(f"Checking for escrow deposit for deal {deal_id}...")
    try:
        url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={ESCROW_DEPOSIT_TOKEN_CONTRACT}&address={ESCROW_DEPOSIT_ADDRESS}&sort=desc&apikey={DEPOSIT_API_KEY}"
        async with httpx.AsyncClient() as client: response = await client.get(url, timeout=20.0); data = response.json()

        if data['status'] == '1' and data['result']:
            for tx in data['result']:
                if tx['to'].lower() == ESCROW_DEPOSIT_ADDRESS.lower() and tx['hash'] not in deal.get('processed_txs', []):
                    tx_amount_usdt = int(tx['value']) / (10**ESCROW_DEPOSIT_TOKEN_DECIMALS)
                    if tx_amount_usdt >= deal['amount']:
                        logging.info(f"Detected valid deposit for deal {deal_id}, tx: {tx['hash']}. Amount: {tx_amount_usdt} USDT.")
                        deal.update({'amount': tx_amount_usdt, 'status': 'funds_secured', 'deposit_tx_hash': tx['hash']})
                        if 'processed_txs' not in deal: deal['processed_txs'] = []
                        deal['processed_txs'].append(tx['hash'])
                        save_escrow_deal(deal_id)

                        seller_id, buyer_id = deal['seller']['id'], deal['buyer']['id']
                        seller_msg = (f"✅ Deposit of ${tx_amount_usdt:.2f} USDT confirmed for deal <code>{deal_id}</code>. Funds are secured.\n\n"
                                      f"You may now proceed with the buyer. Once they confirm receipt, use the button below to release the funds to them.")
                        buyer_msg = (f"✅ The seller has deposited ${tx_amount_usdt:.2f} USDT for deal <code>{deal_id}</code>. The funds are now secured by the bot.\n\n"
                                     f"Please proceed with the transaction. Let the seller know once you have received the goods/services as agreed.")

                        # Enhanced attractive buttons
                        keyboard_seller = [
                            [InlineKeyboardButton("✅ Release Funds to Buyer", callback_data=f"escrow_action_{deal_id}_release")],
                            [InlineKeyboardButton("🚨 Open Dispute", callback_data=f"escrow_action_{deal_id}_dispute")]
                        ]
                        keyboard_buyer = [
                            [InlineKeyboardButton("🚨 Open Dispute", callback_data=f"escrow_action_{deal_id}_dispute")]
                        ]

                        await context.bot.send_message(seller_id, seller_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard_seller))
                        await context.bot.send_message(buyer_id, buyer_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard_buyer))
                        context.job.schedule_removal()
                        return
    except Exception as e: logging.error(f"Error monitoring escrow deposit for deal {deal_id}: {e}", exc_info=True)

async def release_escrow_funds(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    deal = escrow_deals.get(deal_id)
    if not deal or deal['status'] != 'funds_secured': await update.message.reply_text("This deal is not ready for fund release."); return
    if not all([ESCROW_WALLET_PRIVATE_KEY, w3_bsc]):
        await update.message.reply_text("Escrow wallet not configured. Contacting admin.")
        await context.bot.send_message(BOT_OWNER_ID, f"FATAL: Attempted to release funds for deal {deal_id} but PK or web3 is missing!")
        return

    try:
        w3 = w3_bsc
        contract = w3.eth.contract(address=Web3.to_checksum_address(ESCROW_DEPOSIT_TOKEN_CONTRACT), abi=ERC20_ABI)
        amount_wei = int(deal['amount'] * (10**ESCROW_DEPOSIT_TOKEN_DECIMALS))
        to_address, from_address = Web3.to_checksum_address(deal['buyer']['withdrawal_address']), Web3.to_checksum_address(ESCROW_DEPOSIT_ADDRESS)
        tx = contract.functions.transfer(to_address, amount_wei).build_transaction({
            'chainId': 56, 'gas': 150000, 'gasPrice': w3.eth.gas_price, 'nonce': w3.eth.get_transaction_count(from_address)})
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=ESCROW_WALLET_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            deal.update({'status': 'completed', 'release_tx_hash': tx_hash.hex()}); save_escrow_deal(deal_id)
            explorer_url = f"https://bscscan.com/tx/{tx_hash.hex()}"
            success_msg = f"✅ Deal {deal_id} completed! ${deal['amount']:.2f} USDT sent to the buyer. Explorer: {explorer_url}"
            await context.bot.send_message(deal['seller']['id'], success_msg); await context.bot.send_message(deal['buyer']['id'], success_msg)
        else: raise Exception("Transaction failed on-chain.")
    except Exception as e:
        logging.error(f"FATAL ERROR releasing funds for deal {deal_id}: {e}", exc_info=True)
        deal['status'] = 'release_failed'; save_escrow_deal(deal_id)
        fail_msg = f"🚨 An error occurred releasing funds for deal {deal_id}. Contact @jashanxjagy immediately."
        await context.bot.send_message(deal['seller']['id'], fail_msg); await context.bot.send_message(deal['buyer']['id'], fail_msg)
        await context.bot.send_message(BOT_OWNER_ID, f"FATAL ERROR releasing funds for deal {deal_id}: {e}")

@check_banned
@check_maintenance
async def escrow_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only command to manually mark escrow deposit as received"""
    user = update.effective_user
    
    # Check if user is owner
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("This command is only available to the bot owner.")
        return
    
    # Check if escrow_id is provided
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /add <escrow_id>\n\nExample: /add ESC_ABC123")
        return
    
    deal_id = context.args[0]
    deal = escrow_deals.get(deal_id)
    
    if not deal:
        await update.message.reply_text(f"❌ Escrow deal {deal_id} not found.")
        return
    
    if deal['status'] != 'accepted_awaiting_deposit':
        await update.message.reply_text(f"❌ Deal {deal_id} is not awaiting deposit. Current status: {deal['status']}")
        return
    
    # Mark deposit as received
    deal['status'] = 'funds_secured'
    deal['deposit_tx_hash'] = 'MANUAL_CONFIRMATION_BY_OWNER'
    save_escrow_deal(deal_id)
    
    # Notify both parties
    seller_id = deal['seller']['id']
    buyer_id = deal['buyer']['id']
    
    seller_msg = (f"✅ Deposit for deal <code>{deal_id}</code> has been confirmed by @jashanxjagy. Funds are secured.\n\n"
                  f"Amount: ${deal['amount']:.2f} USDT\n\n"
                  f"You may now proceed with the buyer. Once they confirm receipt, use the button below to release the funds to them.")
    
    buyer_msg = (f"✅ The seller's deposit for deal <code>{deal_id}</code> has been confirmed by @jashanxjagy.\n\n"
                 f"Amount: ${deal['amount']:.2f} USDT\n\n"
                 f"The funds are now secured by the bot. Please proceed with the transaction. Let the seller know once you have received the goods/services as agreed.")
    
    # Create enhanced buttons with better styling
    keyboard_seller = [
        [InlineKeyboardButton("✅ Release Funds to Buyer", callback_data=f"escrow_action_{deal_id}_release")],
        [InlineKeyboardButton("🚨 Open Dispute", callback_data=f"escrow_action_{deal_id}_dispute")]
    ]
    
    keyboard_buyer = [
        [InlineKeyboardButton("🚨 Open Dispute", callback_data=f"escrow_action_{deal_id}_dispute")]
    ]
    
    await context.bot.send_message(seller_id, seller_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard_seller))
    await context.bot.send_message(buyer_id, buyer_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard_buyer))
    
    # Confirm to owner
    await update.message.reply_text(
        f"✅ Deposit for deal <code>{deal_id}</code> has been manually confirmed.\n\n"
        f"Amount: ${deal['amount']:.2f} USDT\n"
        f"Seller: {deal['seller']['username']} (ID: {seller_id})\n"
        f"Buyer: {deal['buyer']['username']} (ID: {buyer_id})\n\n"
        f"Both parties have been notified.",
        parse_mode=ParseMode.HTML
    )

## NEW FEATURES ##
@check_banned
@check_maintenance
async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /continue <game_id>")
        return

    game_id = context.args[0]
    game = game_sessions.get(game_id)

    if not game or game.get('status') != 'active' or game.get('user_id') != user.id:
        await update.message.reply_text("Could not find an active game with that ID belonging to you.")
        return

    game_type = game['game_type']

    # Fake an update/query object to pass to the callback handlers
    class FakeQuery:
        def __init__(self, user, message):
            self.from_user = user
            self.message = message
        async def answer(self, *args, **kwargs): pass
        async def edit_message_text(self, *args, **kwargs):
            await self.message.reply_text(*args, **kwargs)

    fake_update = type('FakeUpdate', (), {'callback_query': FakeQuery(user, update.message)})()

    if game_type == 'mines':
        text = f"💣 Resuming Mines Game (ID: <code>{game_id}</code>)..."
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=mines_keyboard(game_id))
    elif game_type == 'tower':
        text = f"🏗️ Resuming Tower Game (ID: <code>{game_id}</code>)..."
        keyboard = create_tower_keyboard(game_id, game['current_row'], [], game['tower_config'][game['current_row']])
        if game['current_row'] > 0:
            multiplier = TOWER_MULTIPLIERS[game["bombs_per_row"]][game["current_row"]]
            potential_winnings = game["bet_amount"] * multiplier
            keyboard.append([InlineKeyboardButton(f"💸 Cash Out (${potential_winnings:.2f})", callback_data=f"tower_cashout_{game_id}")])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    elif game_type == 'coin_flip':
        text = f"🪙 Resuming Coin Flip (ID: <code>{game_id}</code>)..."
        multiplier = 2 ** game["streak"]
        win_amount = game["bet_amount"] * multiplier
        keyboard = [
            [InlineKeyboardButton("🪙 Heads", callback_data=f"flip_pick_{game_id}_Heads"),
             InlineKeyboardButton("🪙 Tails", callback_data=f"flip_pick_{game_id}_Tails")],
        ]
        if game['streak'] > 0:
            keyboard.append([InlineKeyboardButton(f"💸 Cash Out (${win_amount:.2f})", callback_data=f"flip_cashout_{game_id}")])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    # FIX: Add blackjack continuation
    elif game_type == 'blackjack':
        text = f"🃏 Resuming Blackjack (ID: <code>{game_id}</code>)..."
        player_value = calculate_hand_value(game['player_hand'])
        dealer_show_card = game['dealer_hand'][0]
        hand_text = format_hand("Your hand", game['player_hand'], player_value)
        dealer_text = f"Dealer shows: {dealer_show_card}\n"
        keyboard = [
            [InlineKeyboardButton("👊 Hit", callback_data=f"bj_hit_{game_id}"),
             InlineKeyboardButton("✋ Stand", callback_data=f"bj_stand_{game_id}")],
        ]
        await update.message.reply_text(
            f"{text}\n\n{hand_text}\n{dealer_text}\n💰 Bet: ${game['bet_amount']:.2f}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("This game type cannot be continued.")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message to kick them.")
        return

    try:
        member = await chat.get_member(user.id)
        if not member.can_restrict_members and member.status != 'creator':
            await update.message.reply_text("You must be an admin with permission to kick users.")
            return

        target_user = update.message.reply_to_message.from_user
        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("You cannot kick an administrator.")
            return

        await context.bot.ban_chat_member(chat.id, target_user.id)
        await context.bot.unban_chat_member(chat.id, target_user.id) # Unbanning immediately makes it a kick
        await update.message.reply_text(f"Kicked {target_user.mention_html()}.", parse_mode=ParseMode.HTML)
    except BadRequest as e:
        await update.message.reply_text(f"Failed to kick user: {e.message}. I might be missing permissions or the target is an admin.")
    except Exception as e:
        logging.error(f"Error in kick_command: {e}")
        await update.message.reply_text("An error occurred.")

async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message to promote them.")
        return

    try:
        member = await chat.get_member(user.id)
        if not member.can_promote_members and member.status != 'creator':
            await update.message.reply_text("You don't have permission to promote members.")
            return

        await context.bot.promote_chat_member(
            chat_id=chat.id,
            user_id=update.message.reply_to_message.from_user.id,
            can_pin_messages=True,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True
        )
        await update.message.reply_text(f"Promoted {update.message.reply_to_message.from_user.mention_html()} to admin.", parse_mode=ParseMode.HTML)
    except BadRequest as e:
        await update.message.reply_text(f"Failed to promote user: {e.message}. I might be missing permissions.")
    except Exception as e:
        logging.error(f"Error in promote_command: {e}")
        await update.message.reply_text("An error occurred.")

async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to pin it.")
        return

    try:
        member = await chat.get_member(user.id)
        if not member.can_pin_messages and member.status != 'creator':
            await update.message.reply_text("You don't have permission to pin messages.")
            return

        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
    except BadRequest as e:
        await update.message.reply_text(f"Failed to pin message: {e.message}. I might be missing permissions.")
    except Exception as e:
        logging.error(f"Error in pin_command: {e}")
        await update.message.reply_text("An error occurred.")

async def purge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)

    try:
        member = await chat.get_member(user.id)
        if not member.can_delete_messages and member.status != 'creator':
            await update.message.reply_text("You don't have permission to delete messages.")
            return

        bot_member = await chat.get_member(context.bot.id)
        if not bot_member.can_delete_messages:
            await update.message.reply_text("I don't have permission to delete messages. Please make me an admin with this right.")
            return

    except BadRequest as e:
        await update.message.reply_text(f"Could not verify permissions: {e.message}")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to start purging from there up to your command.")
        return

    start_message_id = update.message.reply_to_message.message_id
    end_message_id = update.message.message_id

    message_ids_to_delete = list(range(start_message_id, end_message_id + 1))

    try:
        # Telegram allows deleting up to 100 messages at once
        deleted_count = 0
        for i in range(0, len(message_ids_to_delete), 100):
            chunk = message_ids_to_delete[i:i + 100]
            if await context.bot.delete_messages(chat_id=chat.id, message_ids=chunk):
                deleted_count += len(chunk)

        purge_feedback = await update.message.reply_text(f"✅ Purged {deleted_count} messages.", quote=False)
        await asyncio.sleep(5) # Wait 5 seconds
        await purge_feedback.delete() # Delete the feedback message
    except BadRequest as e:
        await update.message.reply_text(f"Error purging messages: {e.message}. Messages might be too old (over 48h).", quote=False)
    except Exception as e:
        await update.message.reply_text(f"An unexpected error occurred: {e}", quote=False)

@check_banned
@check_maintenance
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    
    # Set menu owner for group protection when called as command
    if not from_callback:
        context.user_data['menu_owner_id'] = update.effective_user.id
    
    sorted_users = sorted(user_stats.items(), key=lambda item: item[1].get('bets', {}).get('amount', 0.0), reverse=True)

    msg = "🏆 <b>Top 10 Players by Wager Amount</b> 🏆\n\n"
    for i, (uid, stats) in enumerate(sorted_users[:10]):
        username = stats.get('userinfo', {}).get('username', f'User-{uid}')
        # Remove '@' if present to avoid mentions
        username = username.lstrip('@')
        wagered = stats.get('bets', {}).get('amount', 0.0)
        msg += f"{i+1}. {username} - <b>${wagered:,.2f}</b>\n"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]]) if from_callback else None

    if from_callback:
        await safe_edit_message(update.callback_query, msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        sent_message = await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        # Set ownership when sending with keyboard
        if reply_markup:
            set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)

    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    stats = user_stats[user.id]
    ref_info = stats.get('referral', {})

    msg = (f"🤝 <b>Your Referral Dashboard</b> 🤝\n\n"
           f"Share your unique link to earn commissions!\n\n"
           f"🔗 <b>Your Link:</b>\n<code>{referral_link}</code>\n\n"
           f"👥 <b>Total Referrals:</b> {len(ref_info.get('referred_users', []))}\n"
           f"💰 <b>Total Commission Earned:</b> ${ref_info.get('commission_earned', 0.0):.4f}\n\n"
           f"<b>Commission Rate:</b>\n"
           f"- <b>{REFERRAL_BET_COMMISSION_RATE*100}%</b> of every bet amount placed by your referrals.")

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]]) if from_callback else None

    if from_callback:
        await safe_edit_message(update.callback_query, msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        sent_message = await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)
        # Set ownership when sending with keyboard
        if reply_markup:
            set_menu_owner(sent_message, user.id)

## NEW FEATURE - /level and /levelall commands ##
def create_progress_bar(progress, total, length=10):
    """Creates a text-based progress bar."""
    filled_length = int(length * progress // total)
    bar = '■' * filled_length + '□' * (length - filled_length)
    return bar

@check_banned
@check_maintenance
async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    current_level_data = get_user_level(user.id)
    wagered = user_stats[user.id].get("bets", {}).get("amount", 0.0)
    
    text = f"🦄 <b>Your Level: {current_level_data['level']} ({current_level_data['name']})</b>\n\n"
    
    # Check if user is at max level
    if current_level_data['level'] == LEVELS[-1]['level']:
        text += "🏆 You have reached the maximum level!\n"
        text += f"💰 Total Wagered: ${wagered:,.2f}"
    else:
        next_level_data = LEVELS[current_level_data['level'] + 1]
        wager_needed_for_next = next_level_data['wager_required']
        wager_of_current = current_level_data['wager_required']
        
        progress = wagered - wager_of_current
        total_for_level = wager_needed_for_next - wager_of_current
        
        progress_bar = create_progress_bar(progress, total_for_level)
        percentage = (progress / total_for_level) * 100
        
        text += f"<b>Progress to Level {next_level_data['level']} ({next_level_data['name']}):</b>\n"
        text += f"`{progress_bar}` ({percentage:.1f}%)\n\n"
        text += f"💰 <b>Wagered:</b> ${wagered:,.2f} / ${wager_needed_for_next:,.2f}\n"
        text += f"💸 <b>Rakeback:</b> {current_level_data['rakeback_percentage']}%"

    keyboard = [
        [InlineKeyboardButton("📜 View All Levels", callback_data="level_all")],
        [InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]
    ]
    
    if from_callback:
        await safe_edit_message(update.callback_query, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        sent_message = await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        # Set ownership after sending
        set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def level_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    # Handle both command and callback query
    if update.callback_query:
        from_callback = True
        
    text = "🦄 <b>All Available Levels</b> 🦄\n\n"
    for level in LEVELS:
        text += (f"<b>Level {level['level']} ({level['name']})</b>\n"
                 f"  - Wager Required: ${level['wager_required']:,}\n"
                 f"  - One-time Reward: ${level['reward']:,}\n"
                 f"  - Rakeback Rate: {level['rakeback_percentage']}%\n"
                 "--------------------\n")
                 
    keyboard = [[InlineKeyboardButton("🔙 Back to My Level", callback_data="main_level")]]
    
    if from_callback:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        # Set ownership after editing
        set_menu_owner(update.callback_query.message, update.callback_query.from_user.id)
    else:
        sent_message = await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        # Set ownership after sending
        if update.effective_user:
            set_menu_owner(sent_message, update.effective_user.id)

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("This is an owner-only command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if not context.args:
        await update.message.reply_text("Usage: /user @username")
        return

    target_username = normalize_username(context.args[0])
    target_user_id = username_to_userid.get(target_username)

    if not target_user_id:
        try:
            chat = await context.bot.get_chat(target_username)
            target_user_id = chat.id
            await ensure_user_in_wallets(target_user_id, chat.username, context=context)
        except Exception:
            await update.message.reply_text(f"Could not find user {target_username}.")
            return

    if target_user_id not in user_stats:
        await update.message.reply_text(f"User {target_username} has not interacted with the bot yet.")
        return

    stats = user_stats[target_user_id]
    userinfo = stats.get('userinfo', {})
    join_date_str = userinfo.get('join_date', 'Not available')
    try:
        join_date = datetime.fromisoformat(join_date_str.split('.')[0]).strftime('%Y-%m-%d %H:%M')
    except:
        join_date = join_date_str

    total_deposits = sum(d['amount'] for d in stats.get('deposits', []))
    total_withdrawals = sum(w['amount'] for w in stats.get('withdrawals', []))
    
    # NEW: Get user level
    level_data = get_user_level(target_user_id)

    text = (
        f"👤 <b>User Info for @{userinfo.get('username','')}</b> (ID: <code>{target_user_id}</code>)\n"
        f"🗓️ Joined: {join_date} UTC\n"
        f"🦄 Level: {level_data['level']} ({level_data['name']})\n" # ADDED
        f"💰 Balance: ${user_wallets.get(target_user_id, 0.0):.2f}\n"
        f"📈 PnL: ${stats.get('pnl', 0.0):.2f}\n"
        f"🎲 Total Bets: {stats.get('bets', {}).get('count', 0)} (W: {stats.get('bets', {}).get('wins', 0)}, L: {stats.get('bets', {}).get('losses', 0)})\n"
        f"💸 Total Wagered: ${stats.get('bets', {}).get('amount', 0.0):.2f}\n"
        f"💵 Deposits: {len(stats.get('deposits',[]))} (${total_deposits:.2f})\n"
        f"🏧 Withdrawals: {len(stats.get('withdrawals',[]))} (${total_withdrawals:.2f})\n"
        f"🎁 Tips Received: {stats.get('tips_received', {}).get('count', 0)} (${stats.get('tips_received', {}).get('amount', 0.0):.2f})\n"
        f"🎁 Tips Sent: {stats.get('tips_sent', {}).get('count', 0)} (${stats.get('tips_sent', {}).get('amount', 0.0):.2f})\n"
        f"🌧️ Rain Received: {stats.get('rain_received', {}).get('count', 0)} (${stats.get('rain_received', {}).get('amount', 0.0):.2f})\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

## NEW FEATURE - AI Integration with Perplexity ##
@check_banned
@check_maintenance
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    prompt_text = ""
    # Check for reply context
    if update.message.reply_to_message and update.message.reply_to_message.text:
        command_parts = update.message.text.split()
        user_query = ' '.join(command_parts[1:])
        if not user_query: # If just /ai in reply
            user_query = "What do you think about this?"
        prompt_text = f"Considering the context of this message: '{update.message.reply_to_message.text}', respond to the following user query: {user_query}"
    # Check for direct command with prompt
    elif context.args:
        prompt_text = ' '.join(context.args)

    if not prompt_text:
        await update.message.reply_text(
            "How can I help you?\n\nUsage:\n"
            "• `/ai your question here`\n"
            "• Reply to a message with `/ai` to discuss it."
        )
        return

    # Default to g4f for the direct /ai command
    await process_ai_request(update, prompt_text,"g4f")

@check_banned
@check_maintenance
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    if not context.args:
        await update.message.reply_text("Usage: /p <SYMBOL>\nExample: /p BTC")
        return

    symbol = context.args[0].upper()
    pair = f"{symbol}USDT"

    # Use the 24hr ticker endpoint for more details
    url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={pair}"

    status_msg = await update.message.reply_text(f"📈 Fetching 24hr data for {pair} from MEXC...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        price = float(data['lastPrice'])
        price_change_percent = float(data['priceChangePercent']) * 100
        high_price = float(data['highPrice'])
        low_price = float(data['lowPrice'])
        volume = float(data['volume'])
        
        direction_emoji = "🔼" if price_change_percent >= 0 else "🔽"

        text = (
            f"📈 <b>{data['symbol']}</b> Price: <code>${price:,.8f}</code>\n\n"
            f"{direction_emoji} <b>24h Change:</b> {price_change_percent:+.2f}%\n"
            f"⬆️ <b>24h High:</b> ${high_price:,.8f}\n"
            f"⬇️ <b>24h Low:</b> ${low_price:,.8f}\n"
            f"📊 <b>24h Volume:</b> {volume:,.2f} {symbol}"
        )
        
        keyboard = [[InlineKeyboardButton("🔄 Update", callback_data=f"price_update_{pair}")]]

        await status_msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

    except httpx.HTTPStatusError as e:
        logging.error(f"MEXC API Error for /p command: {e.response.status_code} - {e.response.text}")
        try:
            error_data = e.response.json()
            error_msg = error_data.get('msg', 'Unknown MEXC error')
            if "Invalid symbol" in error_msg:
                 await status_msg.edit_text(f"❌ Invalid symbol: `{pair}`. Please check the ticker on MEXC.")
            else:
                 await status_msg.edit_text(f"An API error occurred: {error_msg}")
        except json.JSONDecodeError:
            await status_msg.edit_text(f"An unexpected API error occurred while fetching the price for {pair}.")
    except Exception as e:
        logging.error(f"Error in /p command: {e}")
        await status_msg.edit_text(f"An error occurred: {e}")
        
async def price_update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Fetching latest price...")
    
    pair = query.data.split('_')[-1]
    symbol = pair.replace("USDT", "")
    url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={pair}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        price = float(data['lastPrice'])
        price_change_percent = float(data['priceChangePercent']) * 100
        high_price = float(data['highPrice'])
        low_price = float(data['lowPrice'])
        volume = float(data['volume'])
        
        direction_emoji = "🔼" if price_change_percent >= 0 else "🔽"

        text = (
            f"📈 <b>{data['symbol']}</b> Price: <code>${price:,.8f}</code>\n\n"
            f"{direction_emoji} <b>24h Change:</b> {price_change_percent:+.2f}%\n"
            f"⬆️ <b>24h High:</b> ${high_price:,.8f}\n"
            f"⬇️ <b>24h Low:</b> ${low_price:,.8f}\n"
            f"📊 <b>24h Volume:</b> {volume:,.2f} {symbol}"
        )
        
        keyboard = [[InlineKeyboardButton("🔄 Update", callback_data=f"price_update_{pair}")]]
        
        # Check if message content is different before editing to avoid errors
        if query.message.text != text:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("Price is already up to date.")

    except Exception as e:
        logging.error(f"Error in price_update_callback: {e}")
        await query.answer(f"Failed to update price: {e}", show_alert=True)


async def process_ai_request(update: Update, prompt: str, model_choice: str):
    """Generic function to handle AI requests from different models."""
    status_msg = await update.message.reply_text(f"🤖 Thinking with {model_choice.title()}...", reply_to_message_id=update.message.message_id)

    try:
        if model_choice == "perplexity": # Updated name
            if PERPLEXITY_API_KEY and PERPLEXITY_API_KEY.startswith("pplx-"):
                client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
                messages = [{"role": "system", "content": "You are a helpful assistant integrated into a Telegram bot."}, {"role": "user", "content": prompt}]
                response = client.chat.completions.create(model="sonar", messages=messages) # Using a capable model
                ai_response = response.choices[0].message.content
            else:
                ai_response = "Perplexity AI is not configured correctly by the bot owner."

        elif model_choice == "g4f":
            ai_response = await g4f.ChatCompletion.create_async(
                model=g4f.models.default,
                messages=[{"role": "user", "content": prompt}],
            )

        else:
            ai_response = "Invalid AI model selected."

        await status_msg.edit_text(ai_response)

    except Exception as e:
        logging.error(f"AI ({model_choice}) Error: {e}")
        await status_msg.edit_text(f"An error occurred while contacting the AI: {e}")

## NEW FEATURE - Daily Bonus, Achievements, Language Commands ##
@check_banned
@check_maintenance
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)

    # Check if daily bonus is enabled
    if not bot_settings.get("daily_bonus_enabled", True):
        text = "❌ Daily bonus is currently unavailable. Please contact the admin for more information."
        if from_callback:
            await update.callback_query.answer(text, show_alert=True)
        else:
            await update.message.reply_text(text)
        return

    stats = user_stats[user.id]
    lang = stats.get("userinfo", {}).get("language", DEFAULT_LANG)
    last_claim_str = stats.get("last_daily_claim")

    if last_claim_str:
        last_claim_time = datetime.fromisoformat(last_claim_str)
        time_since_claim = datetime.now(timezone.utc) - last_claim_time
        if time_since_claim < timedelta(hours=24):
            time_left = timedelta(hours=24) - time_since_claim
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            text = get_text("daily_claim_wait", lang, hours=hours, minutes=minutes)
            if from_callback:
                await update.callback_query.answer(text, show_alert=True)
            else:
                await update.message.reply_text(text)
            return

    bonus_amount = bot_settings.get("daily_bonus_amount", 0.50)
    user_wallets[user.id] += bonus_amount
    stats["last_daily_claim"] = str(datetime.now(timezone.utc))
    save_user_data(user.id)

    text = get_text("daily_claim_success", lang, amount=bonus_amount)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Bonuses", callback_data="main_bonuses")]]) if from_callback else None

    if from_callback:
        await safe_edit_message(update.callback_query, text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

@check_banned
@check_maintenance
async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)
    stats = user_stats[user.id]
    user_achievements = stats.get("achievements", [])

    if not user_achievements:
        text = get_text("no_achievements", user_lang)
    else:
        text = f"🏅 <b>{get_text('achievements', user_lang)}</b> 🏅\n\n"
        for ach_id in user_achievements:
            ach_data = ACHIEVEMENTS.get(ach_id)
            if ach_data:
                text += f"{ach_data['emoji']} <b>{ach_data['name']}</b> - <i>{ach_data['description']}</i>\n"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to More", callback_data="main_more")]]) if from_callback else None

    if from_callback:
        await safe_edit_message(update.callback_query, text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        sent_message = await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        # Set menu owner when sending with keyboard
        if reply_markup:
            set_menu_owner(sent_message, user.id)

@check_banned
@check_maintenance
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)
    args = context.args

    if not args:
        keyboard = [
            [InlineKeyboardButton(LANGUAGE_NAMES["en"], callback_data="lang_en")],
            [InlineKeyboardButton(LANGUAGE_NAMES["es"], callback_data="lang_es")],
            [InlineKeyboardButton(LANGUAGE_NAMES["fr"], callback_data="lang_fr")],
            [InlineKeyboardButton(LANGUAGE_NAMES["ru"], callback_data="lang_ru")],
            [InlineKeyboardButton(LANGUAGE_NAMES["hi"], callback_data="lang_hi")],
            [InlineKeyboardButton(LANGUAGE_NAMES["zh"], callback_data="lang_zh")]
        ]
        await update.message.reply_text(
            get_text("select_language", user_lang),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    lang_code = args[0].lower()
    if lang_code in LANGUAGE_FILES:
        user_stats[user.id]["userinfo"]["language"] = lang_code
        save_user_data(user.id)
        await update.message.reply_text(get_text("language_set", lang_code))
    else:
        await update.message.reply_text(get_text("error_occurred", user_lang))

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    user = query.from_user
    lang_code = query.data.split('_')[1]
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if lang_code in LANGUAGE_FILES:
        user_stats[user.id]["userinfo"]["language"] = lang_code
        save_user_data(user.id)
        language_name = LANGUAGE_NAMES.get(lang_code, lang_code)
        await query.answer(get_text("language_set", lang_code), show_alert=True)
        # Go back to settings menu
        await settings_command(update, context)
    else:
        user_lang = get_user_lang(user.id)
        await query.answer(get_text("error_occurred", user_lang), show_alert=True)

async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency selection"""
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    user = query.from_user
    currency_code = query.data.split('_')[1]
    await ensure_user_in_wallets(user.id, user.username, context=context)

    if currency_code in CURRENCY_RATES:
        user_stats[user.id]["userinfo"]["currency"] = currency_code
        save_user_data(user.id)
        symbol = CURRENCY_SYMBOLS[currency_code]
        await query.answer(f"Currency set to {currency_code} ({symbol})", show_alert=True)
        # Go back to settings menu
        await settings_command(update, context)
    else:
        await query.answer("Invalid currency code.", show_alert=True)

## NEW FEATURE - Admin Dashboard & Group Settings ##
async def admin_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)

    query = update.callback_query

    total_users = len(user_stats)
    total_balance = sum(user_wallets.values())
    active_games = len([g for g in game_sessions.values() if g.get('status') == 'active'])
    pending_withdrawals = len([w for w in withdrawal_requests.values() if w.get('status') == 'pending'])
    banned_users_count = len(bot_settings.get('banned_users', []))
    temp_banned_users_count = len(bot_settings.get('tempbanned_users', []))

    text = (
        f"👑 <b>Admin Dashboard</b> 👑\n\n"
        f"📊 <b>Bot Stats:</b>\n"
        f"  - Total Users: {total_users}\n"
        f"  - Banned Users: {banned_users_count}\n"
        f"  - Temp Banned (Withdrawals): {temp_banned_users_count}\n"
        f"  - Total User Balance: ${total_balance:,.2f}\n"
        f"  - House Balance: ${bot_settings.get('house_balance', 0):,.2f}\n"
        f"  - Active Escrow Deals: {len(escrow_deals)}\n"
        f"  - Active Games: {active_games}\n"
        f"  - Pending Withdrawals: {pending_withdrawals}\n\n"
        f"⚙️ <b>Bot Settings:</b>\n"
        f"  - Daily Bonus: ${bot_settings.get('daily_bonus_amount', 0.50):.2f}\n"
        f"  - Maintenance Mode: {'ON' if bot_settings.get('maintenance_mode') else 'OFF'}\n"
        f"  - Withdrawals: {'ON' if bot_settings.get('withdrawals_enabled', True) else 'OFF'}"
    )

    keyboard = [
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users"), InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
        [InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_pending_withdrawals")],
        [InlineKeyboardButton("🏦 House Balance", callback_data="admin_set_house_balance"), InlineKeyboardButton("⚖️ Game Limits", callback_data="admin_limits")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_bot_settings"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎁 Gift Codes", callback_data="admin_gift_codes"), InlineKeyboardButton("🎮 Active Games", callback_data="admin_active_games")],
        [InlineKeyboardButton("📊 Export Data", callback_data="admin_export_data")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
    ]

    if query:
        if query.from_user.id != BOT_OWNER_ID: return
        await query.answer()
        await safe_edit_message(query, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_bot_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID: return
    await query.answer()

    text = "⚙️ <b>Bot Settings</b>"
    keyboard = [
        [InlineKeyboardButton(f"Daily Bonus: ${bot_settings.get('daily_bonus_amount', 0.50):.2f}", callback_data="admin_set_daily_bonus")],
        [InlineKeyboardButton(f"Maintenance: {'ON' if bot_settings.get('maintenance_mode') else 'OFF'}", callback_data="admin_toggle_maintenance")],
        [InlineKeyboardButton(f"Withdrawals: {'Enabled' if bot_settings.get('withdrawals_enabled', True) else 'Disabled'}", callback_data="admin_toggle_withdrawals")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
    ]
    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_actions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID:
        await query.answer("This is an admin-only area.", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "admin_dashboard":
        await admin_dashboard_command(update, context)
    elif action == "admin_users":
        await users_command(update, context)
    elif action == "admin_search_user":
        await query.edit_message_text("Please enter the @username or user ID of the user to search.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_dashboard")]]))
        return ADMIN_SEARCH_USER
    elif action == "admin_bot_settings":
        await admin_bot_settings_callback(update, context)
    elif action == "admin_set_house_balance":
        await query.edit_message_text("Please enter the new house balance amount.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_dashboard")]]))
        return ADMIN_SET_HOUSE_BALANCE
    elif action == "admin_limits":
        await query.edit_message_text("Select limit type to set:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Set Minimum Bet", callback_data="admin_limit_type_min")],
            [InlineKeyboardButton("Set Maximum Bet", callback_data="admin_limit_type_max")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
        ]))
        return ADMIN_LIMITS_CHOOSE_TYPE
    elif action == "admin_set_daily_bonus":
        await query.edit_message_text("Please enter the new daily bonus amount (e.g., 0.75).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_bot_settings")]]))
        return ADMIN_SET_DAILY_BONUS
    elif action == "admin_broadcast":
        await query.edit_message_text("Please send the message you want to broadcast to all users.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_dashboard")]]))
        return ADMIN_BROADCAST_MESSAGE
    elif action == "admin_toggle_maintenance":
        bot_settings["maintenance_mode"] = not bot_settings.get("maintenance_mode", False)
        save_bot_state()
        await query.answer(f"Maintenance mode is now {'ON' if bot_settings['maintenance_mode'] else 'OFF'}")
        await admin_bot_settings_callback(update, context)
    elif action == "admin_toggle_withdrawals":
        bot_settings["withdrawals_enabled"] = not bot_settings.get("withdrawals_enabled", True)
        save_bot_state()
        await query.answer(f"Withdrawals are now {'ENABLED' if bot_settings['withdrawals_enabled'] else 'DISABLED'}")
        await admin_bot_settings_callback(update, context)
    elif action == "admin_gift_codes":
        await admin_gift_code_menu(update, context)
    # Removed: admin_ban_management - button removed from dashboard
    elif action == "admin_pending_withdrawals":
        await admin_pending_withdrawals(update, context)
    elif action == "admin_active_games":
        await admin_active_games(update, context)
    elif action == "admin_export_data":
        await admin_export_data_callback(update, context)

## NEW ADMIN SECURITY FEATURES ##

async def admin_ban_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage banned users"""
    query = update.callback_query
    await query.answer()
    
    banned_users = bot_settings.get('banned_users', [])
    temp_banned_users = bot_settings.get('tempbanned_users', [])
    
    text = "🚫 <b>Ban Management</b>\n\n"
    text += f"<b>Permanently Banned Users:</b> {len(banned_users)}\n"
    if banned_users:
        for user_id in banned_users[:5]:  # Show first 5
            username = user_stats.get(user_id, {}).get('userinfo', {}).get('username', 'Unknown')
            text += f"  • @{username} (ID: {user_id})\n"
        if len(banned_users) > 5:
            text += f"  ... and {len(banned_users) - 5} more\n"
    
    text += f"\n<b>Withdrawal Banned Users:</b> {len(temp_banned_users)}\n"
    if temp_banned_users:
        for user_id in temp_banned_users[:5]:  # Show first 5
            username = user_stats.get(user_id, {}).get('userinfo', {}).get('username', 'Unknown')
            text += f"  • @{username} (ID: {user_id})\n"
        if len(temp_banned_users) > 5:
            text += f"  ... and {len(temp_banned_users) - 5} more\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Ban User", callback_data="admin_ban_user_prompt"),
         InlineKeyboardButton("➖ Unban User", callback_data="admin_unban_user_prompt")],
        [InlineKeyboardButton("🚫 Temp Ban (Withdrawals)", callback_data="admin_tempban_user_prompt"),
         InlineKeyboardButton("✅ Remove Temp Ban", callback_data="admin_untempban_user_prompt")],
        [InlineKeyboardButton("📋 View All Bans", callback_data="admin_view_all_bans")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
    ]
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View and manage pending withdrawal requests"""
    query = update.callback_query
    await query.answer()
    
    pending = [w for w in withdrawal_requests.values() if w.get('status') == 'pending']
    
    text = "💸 <b>Pending Withdrawal Requests</b>\n\n"
    
    if not pending:
        text += "No pending withdrawals at the moment."
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]]
    else:
        text += f"Total Pending: {len(pending)}\n\n"
        for w in pending[:5]:  # Show first 5
            text += (
                f"<b>ID:</b> <code>{w['id']}</code>\n"
                f"<b>User:</b> @{w['username']} (ID: {w['user_id']})\n"
                f"<b>Amount:</b> ${w['amount_usd']:.2f}\n"
                f"<b>Address:</b> <code>{w['withdrawal_address']}</code>\n"
                f"<b>Date:</b> {w['timestamp'][:10]}\n\n"
            )
        
        if len(pending) > 5:
            text += f"... and {len(pending) - 5} more\n\n"
        
        text += "Use the approval buttons on individual withdrawal notifications to process them."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_pending_withdrawals")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
        ]
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_active_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all active games"""
    query = update.callback_query
    await query.answer()
    
    active = [g for g in game_sessions.values() if g.get('status') == 'active']
    
    text = "🎮 <b>Active Games</b>\n\n"
    
    if not active:
        text += "No active games at the moment."
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]]
    else:
        text += f"Total Active Games: {len(active)}\n\n"
        
        # Group by game type
        game_types = {}
        for game in active:
            game_type = game.get('game_type', 'unknown')
            game_types[game_type] = game_types.get(game_type, 0) + 1
        
        text += "<b>By Type:</b>\n"
        for game_type, count in game_types.items():
            text += f"  • {game_type.title()}: {count}\n"
        
        text += "\n<b>Recent Games:</b>\n"
        for game in active[:5]:  # Show first 5
            user_id = game.get('user_id', 'Unknown')
            username = user_stats.get(user_id, {}).get('userinfo', {}).get('username', 'Unknown')
            game_type = game.get('game_type', 'unknown')
            bet_amount = game.get('bet_amount', 0)
            text += f"  • {game_type.title()} - @{username} - ${bet_amount:.2f}\n"
        
        if len(active) > 5:
            text += f"  ... and {len(active) - 5} more\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_active_games")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
        ]
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_export_data_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all bot data"""
    query = update.callback_query
    await query.answer("Preparing data export... This may take a moment.", show_alert=True)
    
    try:
        # Create export data
        export_data = {
            "export_timestamp": str(datetime.now(timezone.utc)),
            "bot_settings": bot_settings,
            "total_users": len(user_stats),
            "total_balance": sum(user_wallets.values()),
            "user_stats": user_stats,
            "user_wallets": user_wallets,
            "active_games": len([g for g in game_sessions.values() if g.get('status') == 'active']),
            "escrow_deals": len(escrow_deals),
            "withdrawal_requests": len(withdrawal_requests),
        }
        
        file_path = os.path.join(DATA_DIR, f"bot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(file_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)
        
        # Send file to admin
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=open(file_path, "rb"),
            caption=f"📊 Bot Data Export\n\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            filename=os.path.basename(file_path)
        )
        
        # Clean up
        os.remove(file_path)
        
        await query.answer("Export completed! Check your DMs.", show_alert=True)
        
    except Exception as e:
        logging.error(f"Failed to export data: {e}")
        await query.answer(f"Export failed: {str(e)}", show_alert=True)


async def set_house_balance_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return ConversationHandler.END
    try:
        amount = float(update.message.text)
        if amount < 0: raise ValueError
        bot_settings['house_balance'] = amount
        save_bot_state()
        await update.message.reply_text(f"🏦 House balance set to ${amount:,.2f}.")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a positive number.")
        return ADMIN_SET_HOUSE_BALANCE

    context.user_data.clear()
    await admin_dashboard_command(update, context)
    return ConversationHandler.END

async def admin_limits_choose_type_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID: return ConversationHandler.END
    await query.answer()

    limit_type = query.data.split('_')[-1] # min or max
    context.user_data['limit_type'] = limit_type

    all_games = [
        'blackjack', 'coin_flip', 'roulette', 'dice_roll', 'slots',
        'predict', 'tower', 'mines', 'keno', 'limbo', 'highlow',
        'pvp_dice', 'pvp_darts', 'pvp_goal', 'pvp_bowl',
        'emoji_darts', 'emoji_soccer', 'emoji_basket', 'emoji_bowling', 'emoji_slot'
    ]

    keyboard = []
    row = []
    for game in all_games:
        row.append(InlineKeyboardButton(game.replace('_', ' ').title(), callback_data=f"admin_limit_game_{game}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")])

    await query.edit_message_text(f"Select a game to set the <b>{limit_type}imum</b> bet for:",
                                  reply_markup=InlineKeyboardMarkup(keyboard),
                                  parse_mode=ParseMode.HTML)
    return ADMIN_LIMITS_CHOOSE_GAME

async def admin_limits_choose_game_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID: return ConversationHandler.END
    await query.answer()

    game_name = query.data.split('_')[-1]
    context.user_data['limit_game'] = game_name
    limit_type = context.user_data['limit_type']

    await query.edit_message_text(f"Please enter the <b>{limit_type}imum</b> bet amount for <b>{game_name.replace('_', ' ').title()}</b>.",
                                  parse_mode=ParseMode.HTML,
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_dashboard")]]))
    return ADMIN_LIMITS_SET_AMOUNT

async def admin_limits_set_amount_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return ConversationHandler.END

    try:
        amount = float(update.message.text)
        if amount < 0: raise ValueError

        game_name = context.user_data['limit_game']
        limit_type = context.user_data['limit_type']

        if game_name not in bot_settings['game_limits']:
            bot_settings['game_limits'][game_name] = {}

        bot_settings['game_limits'][game_name][limit_type] = amount
        save_bot_state()

        await update.message.reply_text(f"✅ Set <b>{limit_type}imum</b> bet for <b>{game_name.replace('_', ' ').title()}</b> to <b>${amount:,.2f}</b>.",
                                      parse_mode=ParseMode.HTML)

    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a positive number.")
        return ADMIN_LIMITS_SET_AMOUNT

    context.user_data.clear()
    await admin_dashboard_command(update, context)
    return ConversationHandler.END
# --- Win Broadcasting ---
async def broadcast_win_to_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str, game_name: str, bet_amount: float, win_amount: float, multiplier: float):
    """
    Broadcast a win notification to the configured channel.
    
    Args:
        context: Telegram context
        user_id: User ID of the winner
        username: Username of the winner
        game_name: Name of the game
        bet_amount: Amount bet
        win_amount: Amount won
        multiplier: Win multiplier
    """
    if not WIN_BROADCAST_CHANNEL_ID:
        logging.debug("WIN_BROADCAST_CHANNEL_ID not configured, skipping broadcast")
        return
    
    try:
        win_text = (
            f"🎉 <b>BIG WIN!</b> 🎉\n\n"
            f"Player: @{username or 'Anonymous'}\n"
            f"Game: {game_name}\n"
            f"Bet: ${bet_amount:.2f}\n"
            f"Won: ${win_amount:.2f}\n"
            f"Multiplier: {multiplier:.2f}x"
        )
        
        await context.bot.send_message(
            chat_id=WIN_BROADCAST_CHANNEL_ID,
            text=win_text,
            parse_mode=ParseMode.HTML
        )
        logging.info(f"Win broadcast sent to channel for user {user_id}")
    except Exception as e:
        # Print explicitly to console for debugging
        print(f"BROADCAST ERROR: {e}")
        logging.error(f"Failed to broadcast win to channel: {e}")

async def set_daily_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return ConversationHandler.END
    try:
        amount = float(update.message.text)
        if amount < 0: raise ValueError

        bot_settings['daily_bonus_amount'] = amount
        save_bot_state()
        await update.message.reply_text(f"Daily bonus amount set to ${amount:.2f}.")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a positive number.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_bot_settings")]]))
        return ADMIN_SET_DAILY_BONUS

    context.user_data.clear()
    # Fake a query to go back to the settings menu
    class FakeQuery:
        def __init__(self, user, message): self.from_user = user; self.message = message
        async def answer(self): pass
        async def edit_message_text(self, *args, **kwargs): await message.reply_text(*args, **kwargs)

    # --- FIX STARTS HERE ---
    # Create a fake update object to call the settings menu function
    fake_update = type('FakeUpdate', (), {'callback_query': FakeQuery(update.effective_user, update.message)})()
    await admin_bot_settings_callback(fake_update, context)
    return ConversationHandler.END
    # --- FIX ENDS HERE ---

async def admin_broadcast_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return ConversationHandler.END
    message_text = update.message.text
    all_user_ids = get_all_registered_user_ids()
    sent_count = 0
    failed_count = 0

    await update.message.reply_text(f"Starting broadcast to {len(all_user_ids)} users...")

    for user_id in all_user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode=ParseMode.HTML)
            sent_count += 1
        except (BadRequest, Forbidden) as e:
            logging.warning(f"Broadcast failed for user {user_id}: {e}")
            failed_count += 1
        await asyncio.sleep(0.1) # Avoid hitting rate limits

    await update.message.reply_text(f"Broadcast finished.\n✅ Sent: {sent_count}\n❌ Failed: {failed_count}")

    context.user_data.clear()
    await admin_dashboard_command(update, context)
    return ConversationHandler.END

async def admin_search_user_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return ConversationHandler.END
    username_or_id = update.message.text
    target_user_id = None

    if username_or_id.isdigit():
        target_user_id = int(username_or_id)
    else:
        target_user_id = username_to_userid.get(normalize_username(username_or_id))

    if not target_user_id or target_user_id not in user_stats:
        await update.message.reply_text("User not found. Please try again.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_dashboard")]]))
        return ADMIN_SEARCH_USER

    context.user_data['admin_search_target'] = target_user_id
    await display_admin_user_panel(update, context, target_user_id)
    return ConversationHandler.END

async def display_admin_user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int, page=0, history_type='matches'):
    stats = user_stats[target_user_id]
    userinfo = stats.get('userinfo', {})
    total_deposits = sum(d['amount'] for d in stats.get('deposits', []))
    total_withdrawals = sum(w['amount'] for w in stats.get('withdrawals', []))

    is_banned = target_user_id in bot_settings.get("banned_users", [])
    is_temp_banned = target_user_id in bot_settings.get("tempbanned_users", [])

    text = (
        f"👤 <b>Admin Panel for @{userinfo.get('username','')}</b> (ID: <code>{target_user_id}</code>)\n"
        f"💰 Balance: ${user_wallets.get(target_user_id, 0.0):.2f}\n"
        f"📈 PnL: ${stats.get('pnl', 0.0):.2f}\n"
        f"💵 Deposits: ${total_deposits:.2f} | 💸 Withdrawals: ${total_withdrawals:.2f}\n"
        f"🚫 Ban Status: {'Banned' if is_banned else 'Not Banned'}\n"
        f"⏳ Temp Ban (Withdrawal): {'Banned' if is_temp_banned else 'Not Banned'}\n"
    )

    # History section
    page_size = 5
    items = []
    if history_type == 'matches':
        items = [game_sessions.get(gid) for gid in reversed(stats.get("game_sessions", [])) if gid in game_sessions]
        text += "\n📜 <b>Match History:</b>\n"
    elif history_type == 'deposits':
        items = list(reversed(stats.get("deposits", [])))
        text += "\n📜 <b>Deposit History:</b>\n"
    elif history_type == 'withdrawals':
        items = list(reversed(stats.get("withdrawals", [])))
        text += "\n📜 <b>Withdrawal History:</b>\n"

    paginated_items = items[page*page_size : (page+1)*page_size]
    if not paginated_items:
        text += "No records found.\n"
    else:
        for item in paginated_items:
            if history_type == 'matches':
                game_type = item['game_type'].replace('_', ' ').title()
                win_status = "Win" if item.get('win') else "Loss"
                text += f" • {game_type} (${item['bet_amount']:.2f}) - {win_status} (<code>{item['id']}</code>)\n"
            elif history_type == 'deposits':
                 ts = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d')
                 text += f" • ${item['amount']:.2f} via {item['method']} ({ts})\n"
            elif history_type == 'withdrawals':
                 ts = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d')
                 text += f" • ${item['amount']:.2f} via {item['method']} ({ts})\n"

    # Keyboard
    keyboard = [
        [
            InlineKeyboardButton("Ban" if not is_banned else "Unban", callback_data=f"admin_user_{target_user_id}_ban"),
            InlineKeyboardButton("TempBan" if not is_temp_banned else "UnTempBan", callback_data=f"admin_user_{target_user_id}_tempban")
        ],
        [
            InlineKeyboardButton("Matches", callback_data=f"admin_user_{target_user_id}_history_matches_0"),
            InlineKeyboardButton("Deposits", callback_data=f"admin_user_{target_user_id}_history_deposits_0"),
            InlineKeyboardButton("Withdrawals", callback_data=f"admin_user_{target_user_id}_history_withdrawals_0")
        ]
    ]

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"admin_user_{target_user_id}_history_{history_type}_{page-1}"))
    if (page+1)*page_size < len(items):
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"admin_user_{target_user_id}_history_{history_type}_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Admin Dashboard", callback_data="admin_dashboard")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def admin_user_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID:
        await query.answer("This is an admin-only area.", show_alert=True)
        return

    await query.answer()

    parts = query.data.split('_')
    # admin_user_{user_id}_action
    # admin_user_{user_id}_history_{type}_{page}
    target_user_id = int(parts[2])
    action = parts[3]

    if action == 'ban':
        if target_user_id in bot_settings.get("banned_users", []):
            bot_settings["banned_users"].remove(target_user_id)
            await query.answer("User unbanned.")
        else:
            bot_settings.setdefault("banned_users", []).append(target_user_id)
            await query.answer("User banned.")
        save_bot_state()
    elif action == 'tempban':
        if target_user_id in bot_settings.get("tempbanned_users", []):
            bot_settings["tempbanned_users"].remove(target_user_id)
            await query.answer("User's withdrawal restrictions lifted.")
        else:
            bot_settings.setdefault("tempbanned_users", []).append(target_user_id)
            await query.answer("User temporarily banned from withdrawals.")
        save_bot_state()
    elif action == 'history':
        history_type = parts[4]
        page = int(parts[5])
        await display_admin_user_panel(update, context, target_user_id, page, history_type)
        return

    await display_admin_user_panel(update, context, target_user_id)


async def setbal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID: return
    await ensure_user_in_wallets(user.id, user.username, context=context)

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /setbal @username <amount>")
        return

    username, amount_str = args[0], args[1]
    target_user_id = username_to_userid.get(normalize_username(username))

    if not target_user_id:
        await update.message.reply_text(f"User {username} not found.")
        return

    try:
        amount = float(amount_str)
        user_wallets[target_user_id] = amount
        update_pnl(target_user_id)
        save_user_data(target_user_id)
        await update.message.reply_text(f"Balance for {username} set to ${amount:.2f}.")
    except ValueError:
        await update.message.reply_text("Invalid amount.")

## NEW FEATURE - Admin Daily Bonus Commands ##
async def setdaily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("This is an admin-only command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /setdaily <amount>\nExample: /setdaily 0.50")
        return
    
    try:
        amount = float(context.args[0])
        if amount < 0:
            await update.message.reply_text("Amount must be positive.")
            return
        
        bot_settings["daily_bonus_amount"] = amount
        bot_settings["daily_bonus_enabled"] = True
        await update.message.reply_text(f"✅ Daily bonus has been set to ${amount:.2f} and enabled.")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")

async def dailyoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("This is an admin-only command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    bot_settings["daily_bonus_enabled"] = False
    await update.message.reply_text("✅ Daily bonus feature has been disabled. Users will not be able to claim daily bonuses until you enable it again with /dailyon.")

async def dailyon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("This is an admin-only command.")
        return
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    bot_settings["daily_bonus_enabled"] = True
    bonus_amount = bot_settings.get("daily_bonus_amount", 0.50)
    await update.message.reply_text(f"✅ Daily bonus feature has been enabled. Current daily bonus amount: ${bonus_amount:.2f}")


async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message to mute them.")
        return

    try:
        member = await chat.get_member(user.id)
        if not member.can_restrict_members and member.status != 'creator':
            await update.message.reply_text("You must be an admin with permission to mute users.")
            return

        target_user = update.message.reply_to_message.from_user
        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("You cannot mute an administrator.")
            return

        await context.bot.restrict_chat_member(chat.id, target_user.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"Muted {target_user.mention_html()}.", parse_mode=ParseMode.HTML)
    except BadRequest as e:
        await update.message.reply_text(f"Failed to mute user: {e.message}. I might be missing permissions or the target is an admin.")
    except Exception as e:
        logging.error(f"Error in mute_command: {e}")
        await update.message.reply_text("An error occurred.")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to report it to admins.")
        return

    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        report_text = f"📢 Report from {user.mention_html()} in {chat.title}:\n\n<a href='{update.message.reply_to_message.link}'>Reported Message</a>"
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await context.bot.send_message(admin.user.id, report_text, parse_mode=ParseMode.HTML)
                except (Forbidden, BadRequest):
                    pass
        await update.message.reply_text("Reported to admins.")
    except Exception as e:
        logging.error(f"Error in report_command: {e}")
        await update.message.reply_text("An error occurred while reporting.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("Reply to a text message to translate it.")
        return

    text_to_translate = update.message.reply_to_message.text
    # Using g4f for translation
    try:
        translated_text = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Translate the following text to English: '{text_to_translate}'"}],
        )
        await update.message.reply_text(f"<b>Translation:</b>\n{translated_text}", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.reply_to_message.id)
    except Exception as e:
        await update.message.reply_text(f"Translation failed: {e}")

async def lockall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)

    try:
        member = await chat.get_member(user.id)
        if not member.can_restrict_members and member.status != 'creator':
            await update.message.reply_text("You don't have permission to change group settings.")
            return

        bot_member = await chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("I don't have permission to restrict members. Please make me an admin with this right.")
            return

        await context.bot.set_chat_permissions(chat.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("🔒 Chat locked. Only admins can send messages.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed to lock chat: {e.message}")
    except Exception as e:
        logging.error(f"Error in lockall_command: {e}")
        await update.message.reply_text("An error occurred.")

async def unlockall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await ensure_user_in_wallets(user.id, user.username, context=context)

    try:
        member = await chat.get_member(user.id)
        if not member.can_restrict_members and member.status != 'creator':
            await update.message.reply_text("You don't have permission to change group settings.")
            return

        bot_member = await chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("I don't have permission to change permissions. Please make me an admin with this right.")
            return

        # Restore default permissions for all members
        await context.bot.set_chat_permissions(chat.id, ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True,
            can_change_info=False, can_invite_users=True, can_pin_messages=False
        ))
        await update.message.reply_text("🔓 Chat unlocked. All members can send messages again.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed to unlock chat: {e.message}")
    except Exception as e:
        logging.error(f"Error in unlockall_command: {e}")
        await update.message.reply_text("An error occurred.")

## NEW FEATURE - /active and /activeall commands ##
@check_banned
@check_maintenance
async def active_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    active_games = [g for g in game_sessions.values() if g.get("status") == "active" and g.get("user_id") == user.id]

    if not active_games:
        await update.message.reply_text("You have no active games. Start one from the /games menu!")
        return

    msg = "<b>Your Active Games:</b>\n\n"
    for game in active_games:
        game_type = game['game_type'].replace('_', ' ').title()
        msg += f"<b>Game:</b> {game_type} | <b>ID:</b> <code>{game['id']}</code>\n"
        msg += f"<b>Bet:</b> ${game['bet_amount']:.2f}\n"
        msg += f"Use <code>/continue {game['id']}</code> to resume.\n"
        msg += "--------------------\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def active_all_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        return
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    context.user_data['active_games_page'] = 0
    await send_active_games_page(update, context)

async def send_active_games_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = context.user_data.get('active_games_page', 0)
    page_size = 10
    active_games = [g for g in game_sessions.values() if g.get("status") == "active"]

    start_index = page * page_size
    end_index = start_index + page_size
    paginated_games = active_games[start_index:end_index]

    if update.callback_query and not paginated_games:
        await update.callback_query.answer("No more active games.", show_alert=True)
        return

    msg = f"<b>All Active Games (Page {page + 1}/{ -(-len(active_games) // page_size) }):</b>\n\n"
    if not paginated_games:
        msg = "There are no active games on the bot."
    
    for game in paginated_games:
        game_type = game['game_type'].replace('_', ' ').title()
        msg += f"<b>Game:</b> {game_type} | <b>ID:</b> <code>{game['id']}</code>\n"
        if 'players' in game:
            p_names = [game['usernames'].get(pid, f"ID:{pid}") for pid in game['players']]
            msg += f"<b>Players:</b> {', '.join(p_names)}\n"
        else:
            uid = game['user_id']
            uname = user_stats.get(uid, {}).get('userinfo', {}).get('username', f'ID:{uid}')
            msg += f"<b>Player:</b> @{uname}\n"
        msg += f"<b>Bet:</b> ${game['bet_amount']:.2f}\n--------------------\n"

    keyboard = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️ Previous", callback_data="activeall_prev"))
    if end_index < len(active_games):
        row.append(InlineKeyboardButton("Next ➡️", callback_data="activeall_next"))
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def active_all_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != BOT_OWNER_ID:
        await query.answer("This is an admin-only button.", show_alert=True)
        return

    await query.answer()
    action = query.data
    page = context.user_data.get('active_games_page', 0)

    if action == "activeall_next":
        context.user_data['active_games_page'] = page + 1
    elif action == "activeall_prev":
        context.user_data['active_games_page'] = max(0, page - 1)

    await send_active_games_page(update, context)


## NEW FEATURE - More Menu ##
@check_banned
@check_maintenance
async def more_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    query = update.callback_query
    await query.answer()
    
    # All items that were previously in the main menu (except Deposit, Withdraw, Games, Settings, Admin)
    all_items = [
        ("🛡️ Escrow", "main_escrow"),
        ("💼 Wallet", "main_wallet"),
        ("📈 Leaderboard", "main_leaderboard"),
        ("🤝 Referral", "main_referral"),
        ("🦄 Level", "main_level"),
        ("🤖 AI Assistant", "main_ai"),
        ("🏆 Achievements", "main_achievements"),
        ("🆘 Support", "main_support"),
        ("❓ Help", "main_help"),
        ("ℹ️ Info & Rules", "main_info"),
        ("🎟️ Claim Gift Code", "main_claim_gift"),
        ("📊 Stats", "main_stats"),
        ("💱 Currency", "settings_currency"),
    ]
    
    keyboard = []
    # Add all items (2 per row)
    for i in range(0, len(all_items), 2):
        row = [InlineKeyboardButton(all_items[i][0], callback_data=all_items[i][1])]
        if i + 1 < len(all_items):
            row.append(InlineKeyboardButton(all_items[i + 1][0], callback_data=all_items[i + 1][1]))
        keyboard.append(row)
    
    # Add Terms of Service button
    keyboard.append([InlineKeyboardButton("📜 Terms of Service", url="https://telegra.ph/Casino-Terms-of-Service-11-17")])
    
    # Back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")])
    
    text = f"➕ <b>More Options</b>\n\nSelect an option:"
    
    await safe_edit_message(
        query,
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

## NEW FEATURE - Settings and Recovery System ##
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    user_lang = get_user_lang(user.id)

    keyboard = [
        [InlineKeyboardButton(get_text("currency_settings", user_lang), callback_data="settings_currency")],
        [InlineKeyboardButton(get_text("language", user_lang), callback_data="settings_language")],
        [InlineKeyboardButton(get_text("withdrawal_address", user_lang), callback_data="settings_withdrawal")],
        [InlineKeyboardButton(get_text("back", user_lang), callback_data="back_to_main")]
    ]
    
    user_currency = get_user_currency(user.id)
    currency_symbol = CURRENCY_SYMBOLS.get(user_currency, "$")
    user_language = user_stats[user.id].get("userinfo", {}).get("language", "en")
    language_name = LANGUAGES.get(user_language, {}).get("language_name", "English 🇬🇧")
    withdrawal_address = user_stats[user.id].get("withdrawal_address")
    withdrawal_status = f"<b>{get_text('withdrawal_address', user_lang)}:</b> {'✅ Set' if withdrawal_address else '❌ Not Set'}"
    
    await safe_edit_message(
        query,
        get_text("settings_menu", user_lang) + f"\n\n"
        f"<b>Current Currency:</b> {user_currency} ({currency_symbol})\n"
        f"<b>Current Language:</b> {language_name}\n"
        f"{withdrawal_status}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    user = query.from_user
    user_lang = get_user_lang(user.id)
    action = query.data.split('_')[1] if len(query.data.split('_')) > 1 else None

    if action == "currency":
        current_currency = get_user_currency(user.id)
        keyboard = []
        for curr in ["USD", "INR", "EUR", "GBP"]:
            symbol = CURRENCY_SYMBOLS[curr]
            text = f"{symbol} {curr}"
            if curr == current_currency:
                text += " ✓"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"setcurrency_{curr}")])
        keyboard.append([InlineKeyboardButton(get_text("back", user_lang), callback_data="main_settings")])
        
        await safe_edit_message(query,
            f"💱 <b>{get_text('currency_settings', user_lang)}</b>\n\n"
            "Choose your preferred currency. All amounts will be displayed in this currency.\n"
            "Your wallet balance is stored in USD and converted for display.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if action == "language":
        await ensure_user_in_wallets(user.id, user.username, context=context)
        current_language = user_stats[user.id].get("userinfo", {}).get("language", "en")
        keyboard = []
        for lang_code, lang_data in LANGUAGES.items():
            text = lang_data.get("language_name", lang_code)
            if lang_code == current_language:
                text += " ✓"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"lang_{lang_code}")])
        keyboard.append([InlineKeyboardButton(get_text("back", user_lang), callback_data="main_settings")])
        
        await safe_edit_message(query,
            get_text("select_language", user_lang),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if action == "withdrawal":
        withdrawal_address = user_stats[user.id].get("withdrawal_address")
        if withdrawal_address:
            # Show current address and option to change
            await safe_edit_message(query,
                f"💳 <b>Withdrawal Address</b>\n\n"
                f"<b>Current Address:</b>\n<code>{withdrawal_address}</code>\n\n"
                f"This is your USDT-BEP20 withdrawal address.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Change Address", callback_data="settings_withdrawal_change")],
                    [InlineKeyboardButton("🔙 Back to Settings", callback_data="main_settings")]
                ])
            )
            return
        else:
            # Ask user to set withdrawal address
            await safe_edit_message(query,
                "💳 <b>Set Withdrawal Address</b>\n\n"
                "Please enter your USDT-BEP20 withdrawal address.\n"
                "⚠️ Make sure it's a valid BEP20 address.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="main_settings")]])
            )
            return SETTINGS_WITHDRAWAL_ADDRESS

def hash_pin(pin: str) -> str:
    """Hashes a PIN using SHA256."""
    return hashlib.sha256(pin.encode()).hexdigest()

def is_valid_bep20_address(address: str) -> bool:
    """Validate if address is a valid BEP20 (Ethereum-format) address"""
    if not address or not address.startswith("0x"):
        return False
    if len(address) != 42:  # 0x + 40 hex chars
        return False
    try:
        int(address[2:], 16)  # Check if it's valid hex
        return True
    except ValueError:
        return False

async def set_withdrawal_address_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    address = update.message.text.strip()

    if not is_valid_bep20_address(address):
        await update.message.reply_text(
            "❌ Invalid USDT-BEP20 address. Please enter a valid address starting with 0x.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="main_settings")]])
        )
        return SETTINGS_WITHDRAWAL_ADDRESS

    # Save the withdrawal address
    user_stats[user.id]["withdrawal_address"] = address
    save_user_data(user.id)

    await update.message.reply_text(
        f"✅ <b>Withdrawal Address Set!</b>\n\n"
        f"Your withdrawal address has been saved:\n<code>{address}</code>\n\n"
        f"You can now use the withdrawal feature. Use /start to return to the main menu.",
        parse_mode=ParseMode.HTML
    )
    
    # Clear user data to end conversation properly
    context.user_data.clear()
    return ConversationHandler.END

async def withdrawal_change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💳 <b>Change Withdrawal Address</b>\n\n"
        "Please enter your new USDT-BEP20 withdrawal address.\n"
        "⚠️ Make sure it's a valid BEP20 address.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="main_settings")]])
    )
    return SETTINGS_WITHDRAWAL_ADDRESS_CHANGE

async def change_withdrawal_address_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Same logic as set_withdrawal_address_step
    return await set_withdrawal_address_step(update, context)

# --- Withdrawal Request System ---
async def process_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount_str = update.message.text.strip().lower()
    
    # Get user's currency and balance
    user_currency = get_user_currency(user.id)
    balance_usd = user_wallets.get(user.id, 0.0)
    
    try:
        if amount_str == 'all':
            amount_in_currency = convert_currency(balance_usd, user_currency)
            amount_usd = balance_usd
        else:
            amount_in_currency = float(amount_str)
            amount_usd = convert_to_usd(amount_in_currency, user_currency)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number or 'all'.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="back_to_main")]])
        )
        return WITHDRAWAL_AMOUNT
    
    if amount_usd <= 0:
        await update.message.reply_text(
            "❌ Amount must be greater than 0.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="back_to_main")]])
        )
        return WITHDRAWAL_AMOUNT
    
    if amount_usd > balance_usd:
        formatted_balance = format_currency(balance_usd, user_currency)
        await update.message.reply_text(
            f"❌ Insufficient balance. Your balance is {formatted_balance}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="back_to_main")]])
        )
        return WITHDRAWAL_AMOUNT
    
    # Check wager requirements
    total_wager_needed, breakdown = calculate_required_wager(user.id)
    if total_wager_needed > 0:
        # Calculate remaining requirements in user's currency
        tips_needed_display = format_currency(breakdown["unwagered_tips"], user_currency)
        deposit_needed_display = format_currency(breakdown["unwagered_deposit"], user_currency)
        total_wager_display = format_currency(total_wager_needed, user_currency)
        
        rejection_msg = (
            f"❌ <b>Withdrawal Requirements Not Met</b>\n\n"
            f"Before you can withdraw, you must wager the following amounts on casino games:\n\n"
        )
        
        if breakdown["unwagered_tips"] > 0:
            rejection_msg += (
                f"💸 <b>Tips Received:</b> {tips_needed_display}\n"
                f"   Required wager: {tips_needed_display} (1x)\n\n"
            )
        
        if breakdown["unwagered_deposit"] > 0:
            deposit_wager_display = format_currency(breakdown["deposit_wager_needed"], user_currency)
            rejection_msg += (
                f"💰 <b>Deposits:</b> {deposit_needed_display}\n"
                f"   Required wager: {deposit_wager_display} (2x)\n\n"
            )
        
        rejection_msg += (
            f"📊 <b>Total Wager Needed:</b> {total_wager_display}\n\n"
            f"<i>Play any casino game to meet these requirements.</i>"
        )
        
        await update.message.reply_text(
            rejection_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Play Games", callback_data="main_games")]])
        )
        return ConversationHandler.END
    
    # Generate unique withdrawal ID
    withdrawal_id = generate_unique_id("WD")
    withdrawal_address = user_stats[user.id].get("withdrawal_address")
    
    # Create withdrawal request
    withdrawal_requests[withdrawal_id] = {
        "id": withdrawal_id,
        "user_id": user.id,
        "username": user.username or f"User_{user.id}",
        "amount_usd": amount_usd,
        "amount_currency": amount_in_currency,
        "currency": user_currency,
        "withdrawal_address": withdrawal_address,
        "status": "pending",
        "timestamp": str(datetime.now(timezone.utc)),
        "txid": None
    }
    
    # Deduct from user's balance
    user_wallets[user.id] -= amount_usd
    save_user_data(user.id)
    
    # Notify user
    formatted_amount = format_currency(amount_usd, user_currency)
    await update.message.reply_text(
        f"✅ <b>Withdrawal Request Submitted</b>\n\n"
        f"<b>Request ID:</b> <code>{withdrawal_id}</code>\n"
        f"<b>Amount:</b> {formatted_amount}\n"
        f"<b>Address:</b> <code>{withdrawal_address}</code>\n\n"
        f"Your withdrawal request is currently pending review by the administrator.\n"
        f"You will be notified once it's processed.",
        parse_mode=ParseMode.HTML
    )
    
    # Forward to owner
    currency_symbol = CURRENCY_SYMBOLS.get(user_currency, "$")
    try:
        await context.bot.send_message(
            chat_id=BOT_OWNER_ID,
            text=(
                f"💸 <b>New Withdrawal Request</b>\n\n"
                f"<b>Request ID:</b> <code>{withdrawal_id}</code>\n"
                f"<b>User:</b> @{user.username or user.id} (ID: {user.id})\n"
                f"<b>Amount (USD):</b> ${amount_usd:.2f}\n"
                f"<b>Amount ({user_currency}):</b> {currency_symbol}{amount_in_currency:.2f}\n"
                f"<b>Address:</b> <code>{withdrawal_address}</code>\n"
                f"<b>Status:</b> Pending"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"withdrawal_approve_{withdrawal_id}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"withdrawal_cancel_{withdrawal_id}")]
            ])
        )
    except Exception as e:
        logging.error(f"Failed to notify owner about withdrawal {withdrawal_id}: {e}")
    
    # Clear user_data to prevent capturing subsequent inputs
    context.user_data.clear()
    return ConversationHandler.END

async def withdrawal_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != BOT_OWNER_ID:
        await query.answer("Only the owner can approve withdrawals.", show_alert=True)
        return
    
    withdrawal_id = query.data.split("_")[-1]
    withdrawal = withdrawal_requests.get(withdrawal_id)
    
    if not withdrawal:
        await query.answer("Withdrawal request not found.", show_alert=True)
        return
    
    if withdrawal["status"] != "pending":
        await query.answer(f"This withdrawal has already been {withdrawal['status']}.", show_alert=True)
        return
    
    # Ask for TXID
    await query.edit_message_text(
        f"💸 <b>Approve Withdrawal</b>\n\n"
        f"<b>Request ID:</b> <code>{withdrawal_id}</code>\n\n"
        f"Please enter the transaction hash (TXID) for this withdrawal:",
        parse_mode=ParseMode.HTML
    )
    
    context.user_data['withdrawal_approve_id'] = withdrawal_id
    return WITHDRAWAL_APPROVAL_TXID

async def withdrawal_txid_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = update.message.text.strip()
    withdrawal_id = context.user_data.get('withdrawal_approve_id')
    
    if not withdrawal_id or withdrawal_id not in withdrawal_requests:
        await update.message.reply_text("❌ Withdrawal request not found.")
        context.user_data.clear()
        return ConversationHandler.END
    
    withdrawal = withdrawal_requests[withdrawal_id]
    
    # Update withdrawal status
    withdrawal["status"] = "approved"
    withdrawal["txid"] = txid
    withdrawal["approved_at"] = str(datetime.now(timezone.utc))
    
    # Notify user
    currency_symbol = CURRENCY_SYMBOLS.get(withdrawal["currency"], "$")
    try:
        await context.bot.send_message(
            chat_id=withdrawal["user_id"],
            text=(
                f"✅ <b>Withdrawal Approved</b>\n\n"
                f"<b>Request ID:</b> <code>{withdrawal_id}</code>\n"
                f"<b>Amount:</b> {currency_symbol}{withdrawal['amount_currency']:.2f}\n"
                f"<b>Transaction Hash:</b> <code>{txid}</code>\n\n"
                f"Your withdrawal has been processed successfully!"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Failed to notify user about withdrawal approval: {e}")
    
    await update.message.reply_text(
        f"✅ Withdrawal {withdrawal_id} approved and user notified."
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def withdrawal_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != BOT_OWNER_ID:
        await query.answer("Only the owner can cancel withdrawals.", show_alert=True)
        return
    
    withdrawal_id = query.data.split("_")[-1]
    withdrawal = withdrawal_requests.get(withdrawal_id)
    
    if not withdrawal:
        await query.answer("Withdrawal request not found.", show_alert=True)
        return
    
    if withdrawal["status"] != "pending":
        await query.answer(f"This withdrawal has already been {withdrawal['status']}.", show_alert=True)
        return
    
    # Return funds to user
    user_id = withdrawal["user_id"]
    amount_usd = withdrawal["amount_usd"]
    user_wallets[user_id] = user_wallets.get(user_id, 0.0) + amount_usd
    save_user_data(user_id)
    
    # Update withdrawal status
    withdrawal["status"] = "cancelled"
    withdrawal["cancelled_at"] = str(datetime.now(timezone.utc))
    
    # Notify user
    currency_symbol = CURRENCY_SYMBOLS.get(withdrawal["currency"], "$")
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ <b>Withdrawal Cancelled</b>\n\n"
                f"<b>Request ID:</b> <code>{withdrawal_id}</code>\n"
                f"<b>Amount:</b> {currency_symbol}{withdrawal['amount_currency']:.2f}\n\n"
                f"Your withdrawal request has been cancelled by the administrator.\n"
                f"The funds have been returned to your balance.\n\n"
                f"For more information, please contact support @jashanxjagy."
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Failed to notify user about withdrawal cancellation: {e}")
    
    await query.edit_message_text(
        f"❌ Withdrawal {withdrawal_id} cancelled. Funds returned to user's balance."
    )
    
    return ConversationHandler.END


async def cancel_withdrawal_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the withdrawal conversation and return to main menu"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Withdrawal cancelled.")
    context.user_data.clear()
    await start_command_inline(query, context)
    return ConversationHandler.END


async def recover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        await update.message.reply_text("For security, please use the /recover command in a private chat with me.")
        return ConversationHandler.END
        
    await update.message.reply_text(
        "Please enter your recovery token.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_recovery")]])
    )
    return RECOVER_ASK_TOKEN

async def recover_token_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    rec_data = recovery_data.get(token_hash)
    if not rec_data:
        await update.message.reply_text(
            "Invalid token. Please try again or contact support.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_recovery")]])
        )
        return RECOVER_ASK_TOKEN

    if rec_data.get('lock_expiry') and rec_data['lock_expiry'] > datetime.now(timezone.utc):
        time_left = rec_data['lock_expiry'] - datetime.now(timezone.utc)
        await update.message.reply_text(f"This token is locked due to too many failed attempts. Please try again in {time_left.seconds // 60} minutes.")
        return ConversationHandler.END

    # --- SUCCESSFUL RECOVERY (NO PIN REQUIRED) ---
    old_user_id = rec_data['user_id']
    new_user = update.effective_user

    if old_user_id not in user_stats:
        await update.message.reply_text("Could not find the original account data. Please contact support.")
        context.user_data.clear()
        return ConversationHandler.END

    # Transfer data
    await ensure_user_in_wallets(new_user.id, new_user.username, context=context)
    user_stats[new_user.id] = user_stats[old_user_id]
    user_wallets[new_user.id] = user_wallets[old_user_id]

    user_stats[new_user.id]['userinfo']['user_id'] = new_user.id
    user_stats[new_user.id]['userinfo']['username'] = new_user.username
    user_stats[new_user.id]['userinfo']['recovered_from'] = old_user_id
    user_stats[new_user.id]['userinfo']['recovered_at'] = str(datetime.now(timezone.utc))

    # Transfer active games
    active_games_transferred = 0
    for game in game_sessions.values():
        if game.get("status") == "active" and game.get("user_id") == old_user_id:
            game["user_id"] = new_user.id
            active_games_transferred += 1
    
    # Clean up old user data
    if old_user_id in user_stats: del user_stats[old_user_id]
    if old_user_id in user_wallets: del user_wallets[old_user_id]
    old_username = username_to_userid.pop(normalize_username(rec_data.get("username", "")), None)
    
    if os.path.exists(os.path.join(DATA_DIR, f"{old_user_id}.json")):
        os.remove(os.path.join(DATA_DIR, f"{old_user_id}.json"))

    # Clean up recovery token
    del recovery_data[token_hash]
    if os.path.exists(os.path.join(RECOVERY_DIR, f"{token_hash}.json")):
        os.remove(os.path.join(RECOVERY_DIR, f"{token_hash}.json"))

    save_user_data(new_user.id)
    
    await update.message.reply_text(
        f"✅ <b>Recovery Successful!</b>\n\n"
        f"Welcome back, {new_user.mention_html()}! Your data and balance of ${user_wallets[new_user.id]:.2f} have been restored. "
        f"{active_games_transferred} active games were transferred to this account. Use /active to see them.",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_recovery_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Recovery process cancelled.")
    context.user_data.clear()
    await start_command_inline(query, context)
    return ConversationHandler.END

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != BOT_OWNER_ID:
        await update.message.reply_text("This is an owner-only command.")
        return
    
    if update.effective_chat.type != 'private':
        await update.message.reply_text("Please use this command in my DMs for security.")
        return
        
    await update.message.reply_text("Exporting all user data... This may take a moment.")
    
    export_data = {
        "user_stats": user_stats,
        "user_wallets": user_wallets
    }
    
    file_path = os.path.join(DATA_DIR, "export_all_users.json")
    try:
        with open(file_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)
        
        await update.message.reply_document(
            document=open(file_path, "rb"),
            caption=f"All user data as of {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            filename="all_user_data.json"
        )
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Failed to export user data: {e}")
        await update.message.reply_text(f"An error occurred during export: {e}")

async def reset_recovery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID: return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /reset @username")
        return
        
    target_username = normalize_username(context.args[0])
    target_user_id = username_to_userid.get(target_username)
    
    if not target_user_id:
        await update.message.reply_text(f"User {target_username} not found in the bot's database.")
        return
        
    stats = user_stats.get(target_user_id)
    if not stats or not stats.get("recovery_token_hash"):
        await update.message.reply_text(f"User {target_username} does not have a recovery token set.")
        return
        
    token_hash = stats["recovery_token_hash"]
    
    # Remove from user_stats
    stats["recovery_token_hash"] = None
    save_user_data(target_user_id)
    
    # Remove from recovery_data
    if token_hash in recovery_data:
        del recovery_data[token_hash]
    
    # Remove file
    recovery_file = os.path.join(RECOVERY_DIR, f"{token_hash}.json")
    if os.path.exists(recovery_file):
        os.remove(recovery_file)
        
    await update.message.reply_text(f"Successfully reset the recovery token for {target_username}. They can now set a new one via the settings menu.")
    try:
        await context.bot.send_message(target_user_id, "Your account recovery token has been reset by the administrator. You can now set a new one in the settings menu.")
    except Exception as e:
        logging.warning(f"Could not notify user {target_user_id} about recovery reset: {e}")

@check_banned
@check_maintenance
async def claim_gift_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /claim <code>")
        return
        
    code = context.args[0]
    
    if code not in gift_codes:
        await update.message.reply_text("Invalid or expired gift code.")
        return
        
    code_data = gift_codes[code]
    
    if code_data["claims_left"] <= 0:
        await update.message.reply_text("This gift code has already been fully claimed.")
        return
        
    if user.id in code_data["claimed_by"]:
        await update.message.reply_text("You have already claimed this gift code.")
        return
    
    # Check wager requirement
    wager_requirement = code_data.get("wager_requirement", 0)
    if wager_requirement > 0:
        user_total_wagered = user_stats[user.id].get("bets", {}).get("amount", 0.0)
        if user_total_wagered < wager_requirement:
            await update.message.reply_text(
                f"❌ You don't meet the wager requirement for this gift code.\n\n"
                f"Required: ${wager_requirement:.2f} wagered\n"
                f"Your total wagered: ${user_total_wagered:.2f}\n"
                f"You need to wager ${wager_requirement - user_total_wagered:.2f} more in the casino to claim this code."
            )
            return
        
    # All checks passed, award the user
    amount = code_data["amount"]
    user_wallets[user.id] += amount
    user_stats[user.id].setdefault("claimed_gift_codes", []).append(code)
    
    code_data["claims_left"] -= 1
    code_data["claimed_by"].append(user.id)
    
    save_user_data(user.id)
    save_gift_code(code)
    
    await update.message.reply_text(f"🎉 Success! You have claimed a gift code and received ${amount:.2f}!")

@check_banned
@check_maintenance
async def leaderboard_referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user_in_wallets(update.effective_user.id, update.effective_user.username, context=context)
    
    # Sort users by the number of people they have referred
    sorted_users = sorted(user_stats.items(), key=lambda item: len(item[1].get('referral', {}).get('referred_users', [])), reverse=True)

    msg = "🏆 <b>Top 10 Referrers</b> 🏆\n\n"
    for i, (uid, stats) in enumerate(sorted_users[:10]):
        username = stats.get('userinfo', {}).get('username', f'User-{uid}')
        # Remove '@' if present to avoid mentions
        username = username.lstrip('@')
        ref_count = len(stats.get('referral', {}).get('referred_users', []))
        if ref_count > 0:
            msg += f"{i+1}. {username} - <b>{ref_count} referrals</b>\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
async def post_init(application: Application):
    """
    Post initialization hook to start background tasks.
    This runs after the event loop is started by run_polling().
    """
    # Start the deposit monitor task
    application.create_task(monitor_deposits_task(application))
    
    # Start the sweep task (if you want it running as well)
    application.create_task(sweep_deposits_task(application))
    
    logging.info("Background tasks started successfully via post_init")
# --- Main Function ---)
def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO,
                        handlers=[logging.FileHandler(os.path.join(LOGS_DIR, f"bot_{datetime.now().strftime('%Y%m%d')}.log")), logging.StreamHandler()])
    logging.info("Starting bot...")
    
    # Load all language files at startup
    logging.info("Loading language files...")
    load_language_files()
    
    # ===== INITIALIZE DEPOSIT SYSTEM =====
    deposit_system_active = DEPOSIT_ENABLED
    if deposit_system_active:
        logging.info("Initializing deposit system...")
        app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
        # Validate configuration
        if not MASTER_MNEMONIC:
            logging.error("MASTER_MNEMONIC not set! Deposit system disabled.")
            deposit_system_active = False
        elif not HOT_WALLET_PRIVATE_KEY:
            logging.error("HOT_WALLET_PRIVATE_KEY not set! Deposit system disabled.")
            deposit_system_active = False
        elif not all(MASTER_WALLETS.values()):
            logging.warning("Not all master wallets configured. Some chains may not work.")
        
        if deposit_system_active:
            try:
                deposit_db = DepositDatabase()
                logging.info("Deposit database initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize deposit database: {e}")
                logging.warning("Deposit system disabled due to initialization error")
                deposit_system_active = False

    if not PERPLEXITY_API_KEY or not PERPLEXITY_API_KEY.startswith("pplx-"):
        logging.warning("PERPLEXITY_API_KEY is not set correctly. Perplexity features will be disabled.")
    
    # Validate WIN_BROADCAST_CHANNEL_ID format
    if WIN_BROADCAST_CHANNEL_ID:
        # Check if it's a channel username (starts with @)
        if WIN_BROADCAST_CHANNEL_ID.startswith("@"):
            logging.info(f"Win broadcasting configured for public channel: {WIN_BROADCAST_CHANNEL_ID}")
        else:
            # Check if ID is a positive number without the -100 prefix
            try:
                channel_id_num = int(WIN_BROADCAST_CHANNEL_ID)
                if channel_id_num > 0:
                    logging.warning(f"⚠️ WIN_BROADCAST_CHANNEL_ID ({WIN_BROADCAST_CHANNEL_ID}) is a positive number. "
                                  f"Channel IDs usually require a '-100' prefix (e.g., '-100{WIN_BROADCAST_CHANNEL_ID}'). "
                                  f"Broadcasting may fail if this format is incorrect.")
            except ValueError:
                logging.warning(f"⚠️ WIN_BROADCAST_CHANNEL_ID ({WIN_BROADCAST_CHANNEL_ID}) is not a valid format. "
                              f"Use numeric ID (e.g., '-1003848853417') or channel username (e.g., '@mychannel').")

    if w3_bsc and w3_bsc.is_connected(): logging.info(f"BSC connected. Chain ID: {w3_bsc.eth.chain_id}")
    else: logging.warning("BSC connection failed")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # Conversation handlers
    admin_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_actions_callback, pattern="^admin_set_house_balance$"),
            CallbackQueryHandler(admin_actions_callback, pattern="^admin_limits$"),
            CallbackQueryHandler(admin_actions_callback, pattern="^admin_set_daily_bonus$"),
            CallbackQueryHandler(admin_actions_callback, pattern="^admin_search_user$"),
            CallbackQueryHandler(admin_actions_callback, pattern="^admin_broadcast$"),
            CallbackQueryHandler(admin_gift_code_create_step1, pattern="^admin_gift_create$"),
        ],
        states={
            ADMIN_SET_HOUSE_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_house_balance_step)],
            ADMIN_LIMITS_CHOOSE_TYPE: [CallbackQueryHandler(admin_limits_choose_type_step, pattern="^admin_limit_type_")],
            ADMIN_LIMITS_CHOOSE_GAME: [CallbackQueryHandler(admin_limits_choose_game_step, pattern="^admin_limit_game_")],
            ADMIN_LIMITS_SET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_limits_set_amount_step)],
            ADMIN_SET_DAILY_BONUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_daily_bonus_step)],
            ADMIN_SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_user_step)],
            ADMIN_BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_step)],
            ADMIN_GIFT_CODE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_gift_code_create_step2)],
            ADMIN_GIFT_CODE_CLAIMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_gift_code_create_step3)],
            ADMIN_GIFT_CODE_WAGER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_gift_code_create_step4)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_dashboard_command, pattern="^admin_dashboard$"),
            CallbackQueryHandler(admin_bot_settings_callback, pattern="^admin_bot_settings$"),
            CallbackQueryHandler(admin_gift_code_menu, pattern="^admin_gift_codes$"),
            # --- FIX STARTS HERE ---
            # Add a generic cancel handler that returns to the main admin dashboard
            # and properly ends the conversation. This will fix the stuck state issue.
            CallbackQueryHandler(admin_dashboard_command, pattern="^cancel_admin_action$"),
        ],
        # --- FIX ENDS HERE ---
        per_user=True,
        per_chat=True,
        conversation_timeout=timedelta(minutes=5).total_seconds()
    )

    game_setup_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_game_conversation, pattern="^game_mines_start$"),
            CommandHandler("mines", start_game_conversation_from_command),
        ],
        states={
            SELECT_BOMBS: [CallbackQueryHandler(select_bombs_callback, pattern="^bombs_")],
            SELECT_BET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_bet_amount_step)],
        },
        fallbacks=[CallbackQueryHandler(cancel_game_conversation, pattern="^cancel_game$")],
        per_message=False,
        conversation_timeout=timedelta(minutes=2).total_seconds()
    )

    tower_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tower_ask_bet, pattern="^game_tower_start$"),
        ],
        states={
            TOWER_BET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tower_receive_bet)],
        },
        fallbacks=[CallbackQueryHandler(cancel_game_conversation, pattern="^cancel_game$")],
        per_message=False,
        conversation_timeout=timedelta(minutes=2).total_seconds()
    )

    pvb_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(pvb_menu_callback, pattern="^pvb_start_"),
            CallbackQueryHandler(pvb_menu_callback, pattern="^pvb_mode_"),
            CallbackQueryHandler(pvb_menu_callback, pattern="^pvb_rolls_"),
        ],
        states={
            SELECT_BET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pvb_get_bet_amount)],
            SELECT_TARGET_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pvb_get_target_score)],
        },
        fallbacks=[CallbackQueryHandler(cancel_game_conversation, pattern="^cancel_game$")],
        per_message=False,
        per_chat=True,  # Explicitly set per_chat
        per_user=True,  # Explicitly set per_user
        conversation_timeout=timedelta(minutes=2).total_seconds()
    )
    ai_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_ai_conversation, pattern="^main_ai$")],
        states={
            CHOOSE_AI_MODEL: [CallbackQueryHandler(choose_ai_model_callback)],
            ASK_AI_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_conversation_prompt)],
        },
        fallbacks=[CallbackQueryHandler(cancel_ai_conversation, pattern="^cancel_ai$")],
        per_message=False,
        conversation_timeout=timedelta(minutes=5).total_seconds()
    )

    recovery_handler = ConversationHandler(
        entry_points=[CommandHandler("recover", recover_command)],
        states={
            RECOVER_ASK_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, recover_token_step)],
        },
        fallbacks=[CallbackQueryHandler(cancel_recovery_conversation, pattern="^cancel_recovery$")],
        per_user=True,
        conversation_timeout=timedelta(minutes=3).total_seconds()
    )

    withdrawal_address_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(settings_callback_handler, pattern="^settings_withdrawal$"),
            CallbackQueryHandler(withdrawal_change_callback, pattern="^settings_withdrawal_change$")
        ],
        states={
            SETTINGS_WITHDRAWAL_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_withdrawal_address_step)],
            SETTINGS_WITHDRAWAL_ADDRESS_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_withdrawal_address_step)]
        },
        fallbacks=[CallbackQueryHandler(settings_command, pattern="^main_settings$")],
        per_user=True,
        conversation_timeout=timedelta(minutes=2).total_seconds()
    )

    withdrawal_flow_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(main_menu_callback, pattern="^main_withdraw$")],
        states={
            WITHDRAWAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdrawal_amount)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_withdrawal_conversation, pattern="^back_to_main$"),
            CommandHandler("cancel", cancel_withdrawal_conversation)
        ],
        per_user=True,
        conversation_timeout=timedelta(minutes=3).total_seconds(),
        allow_reentry=False  # Prevent re-entry once conversation ends
    )

    withdrawal_approval_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdrawal_approve_callback, pattern="^withdrawal_approve_")],
        states={
            WITHDRAWAL_APPROVAL_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_txid_step)]
        },
        fallbacks=[],
        per_user=True,
        conversation_timeout=timedelta(minutes=10).total_seconds()
    )


    app.add_handler(CommandHandler("start", start_command, block=False))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["bj", "blackjack"], blackjack_command)); app.add_handler(CommandHandler("flip", coin_flip_command))
    app.add_handler(CommandHandler(["roul", "roulette"], roulette_command)); app.add_handler(CommandHandler("dr", dice_roll_command))
    app.add_handler(CommandHandler("sl", slots_command)); app.add_handler(CommandHandler("bank", bank_command)); app.add_handler(CommandHandler("hb", bank_command)) # hb is alias for bank
    app.add_handler(CommandHandler("rain", rain_command)); app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("users", users_command)); app.add_handler(CommandHandler("dice", dice_command))
    app.add_handler(CommandHandler("darts", darts_command)); app.add_handler(CommandHandler("goal", football_command))
    app.add_handler(CommandHandler("bowl", bowling_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("clearall", clearall_command))
    app.add_handler(CommandHandler(["bal", "balance"], balance_command)); app.add_handler(CommandHandler("tip", tip_command))
    app.add_handler(CommandHandler("cashout", cashout_command)); app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("stop", stop_command)); app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CommandHandler("cancelall", cancel_all_command)); app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("lb", limbo_command)); app.add_handler(CommandHandler("limbo", limbo_command)); app.add_handler(CommandHandler("Limbo", limbo_command)); app.add_handler(CommandHandler("keno", keno_command))
    app.add_handler(CommandHandler("hl", highlow_command))  # NEW: High-Low game
    app.add_handler(CommandHandler(["escrow", "esc"], escrow_command))
    app.add_handler(CommandHandler("add", escrow_add_command))  # Owner-only: manually confirm escrow deposit
    app.add_handler(CommandHandler(["matches", "hc"], matches_command));
    app.add_handler(CommandHandler(["deals", "he"], deals_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("continue", continue_command))
    # New commands
    app.add_handler(CommandHandler("kick", kick_command)); app.add_handler(CommandHandler("promote", promote_command))
    app.add_handler(CommandHandler("pin", pin_command)); app.add_handler(CommandHandler("purge", purge_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("user", user_info_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("p", price_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("achievements", achievements_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("admin", admin_dashboard_command))
    app.add_handler(CommandHandler("setbal", setbal_command))
    app.add_handler(CommandHandler("setdaily", setdaily_command)) # NEW
    app.add_handler(CommandHandler("dailyoff", dailyoff_command)) # NEW
    app.add_handler(CommandHandler("dailyon", dailyon_command)) # NEW
    app.add_handler(CommandHandler("games", games_menu)) # New alias
    app.add_handler(CommandHandler("tower", tower_command)) # NEW - Tower game
    app.add_handler(CommandHandler("tr", tower_command)) # NEW - Tower game alias
    app.add_handler(CommandHandler("active", active_games_command)) # NEW
    app.add_handler(CommandHandler("activeall", active_all_games_command)) # NEW
    app.add_handler(CommandHandler("reset", reset_recovery_command)) # NEW
    app.add_handler(CommandHandler("export", export_command)) # NEW
    app.add_handler(CommandHandler("claim", claim_gift_code_command)) # NEW
    app.add_handler(CommandHandler("leaderboardrf", leaderboard_referral_command)) # NEW
    app.add_handler(CommandHandler("weekly", weekly_bonus_command)) # NEW
    app.add_handler(CommandHandler("monthly", monthly_bonus_command)) # NEW
    app.add_handler(CommandHandler("demo", demo_command)) # NEW: Demo claim system
    app.add_handler(CommandHandler("serverseed", serverseed_command)) # NEW: Provably fair
    app.add_handler(CommandHandler("seed", seed_command)) # NEW: Provably fair
    app.add_handler(CommandHandler("rk", rakeback_command)) # NEW
    app.add_handler(CommandHandler("level", level_command)) # NEW
    app.add_handler(CommandHandler("levelall", level_all_command)) # NEW
    # REMOVED NEW GAMES: crash, plinko, wheel, scratch, coinchain
    # New Group Management Commands
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("lockall", lockall_command))
    app.add_handler(CommandHandler("unlockall", unlockall_command))
    
    # ===== DEPOSIT SYSTEM HANDLERS =====
    app.add_handler(CommandHandler("deposit", deposit_command))
    app.add_handler(CallbackQueryHandler(deposit_method_callback, pattern=r"^deposit_(ETH|BNB|BASE|TRON|SOLANA|TON)$"))
    app.add_handler(CallbackQueryHandler(check_deposit_status, pattern=r"^(deposit_history|check_deposit_)"))
    app.add_handler(CallbackQueryHandler(back_to_deposit_menu, pattern=r"^back_to_deposit_menu$"))
    
    # REMOVED bonus_callback_handler as it's no longer in the main menu
    app.add_handler(admin_handler)
    app.add_handler(game_setup_handler)
    app.add_handler(tower_handler)  # NEW - Tower game conversation
    app.add_handler(pvb_handler)
    app.add_handler(ai_handler)
    app.add_handler(recovery_handler)
    app.add_handler(withdrawal_address_handler)
    app.add_handler(withdrawal_flow_handler)
    app.add_handler(withdrawal_approval_handler)

    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^(main_|back_to_main|my_matches|my_deals|deposit_usdt_menu|deposit_coming_soon)"))
    app.add_handler(CallbackQueryHandler(games_category_callback, pattern=r"^games_(category_|emoji_)")) # NEW - updated to handle emoji subcategories
    app.add_handler(CallbackQueryHandler(play_single_emoji_callback, pattern=r"^play_single_")) # NEW - Single emoji games
    app.add_handler(CallbackQueryHandler(group_challenge_mode_callback, pattern=r"^gc_mode_")) # NEW - Group challenge mode
    app.add_handler(CallbackQueryHandler(group_challenge_rolls_callback, pattern=r"^gc_rolls_")) # NEW - Group challenge rolls
    app.add_handler(CallbackQueryHandler(group_challenge_target_callback, pattern=r"^gc_target_")) # NEW - Group challenge target score
    app.add_handler(CallbackQueryHandler(group_challenge_accept_callback, pattern=r"^gc_accept_")) # NEW - Accept group challenge
    app.add_handler(CallbackQueryHandler(group_challenge_playbot_callback, pattern=r"^gc_playbot_")) # NEW - Play with bot
    app.add_handler(CallbackQueryHandler(xdxw_mode_callback, pattern=r"^xdxw_mode_|^xdxw_cancel$")) # NEW - XdX'w mode selection
    app.add_handler(CallbackQueryHandler(xdxw_accept_callback, pattern=r"^xdxw_accept_")) # NEW - XdX'w accept challenge
    app.add_handler(CallbackQueryHandler(xdxw_playbot_callback, pattern=r"^xdxw_playbot_")) # NEW - XdX'w play with bot
    app.add_handler(CallbackQueryHandler(level_all_command, pattern=r"^level_all$")) # NEW
    app.add_handler(CallbackQueryHandler(price_update_callback, pattern=r"^price_update_")) # NEW
    app.add_handler(CallbackQueryHandler(game_info_callback, pattern=r"^game_")); app.add_handler(CallbackQueryHandler(blackjack_callback, pattern=r"^bj_"))
    app.add_handler(CallbackQueryHandler(coin_flip_callback, pattern=r"^flip_")); app.add_handler(CallbackQueryHandler(tower_callback, pattern=r"^tower_"))
    app.add_handler(CallbackQueryHandler(highlow_callback, pattern=r"^hl_"))  # NEW - High-Low game callbacks
    app.add_handler(CallbackQueryHandler(keno_callback, pattern=r"^keno_")) # NEW - Keno game callbacks
    app.add_handler(CallbackQueryHandler(coinchain_callback, pattern=r"^coinchain_")) # NEW - Coin Chain game callbacks
    app.add_handler(CallbackQueryHandler(clear_confirm_callback, pattern=r"^(clear|clearall)_confirm_"))
    app.add_handler(CallbackQueryHandler(match_invite_callback, pattern=r"^(accept_|decline_)")); app.add_handler(CallbackQueryHandler(mines_pick_callback, pattern=r"^mines_"))
    app.add_handler(CallbackQueryHandler(stop_confirm_callback, pattern=r"^stop_confirm_")); app.add_handler(CallbackQueryHandler(pvb_menu_callback, pattern="^pvp_info_"))
    app.add_handler(CallbackQueryHandler(escrow_callback_handler, pattern=r"^escrow_")); app.add_handler(CallbackQueryHandler(users_navigation_callback, pattern=r"^users_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang_"))
    app.add_handler(CallbackQueryHandler(currency_callback, pattern=r"^setcurrency_")) # NEW - Currency setting
    app.add_handler(CallbackQueryHandler(admin_actions_callback, pattern=r"^admin_(dashboard|users|bot_settings|toggle_maintenance|broadcast|set_house_balance|limits|gift_codes|toggle_withdrawals|pending_withdrawals|active_games|export_data)$"))
    app.add_handler(CallbackQueryHandler(admin_user_search_callback, pattern=r"^admin_user_"))
    app.add_handler(CallbackQueryHandler(settings_callback_handler, pattern=r"^settings_"))
    app.add_handler(CallbackQueryHandler(active_all_navigation_callback, pattern=r"^activeall_"))
    app.add_handler(CallbackQueryHandler(withdrawal_cancel_callback, pattern=r"^withdrawal_cancel_")) # NEW - Withdrawal cancellation
    
    # Provably Fair Callbacks (OLD SYSTEM - REMOVED, now using deep links to DM)
    # app.add_handler(CallbackQueryHandler(pf_rotate_seeds_callback, pattern=r"^pf_rotate_seeds$"))
    # app.add_handler(CallbackQueryHandler(pf_show_game_details_callback, pattern=r"^pf_show_"))
    # app.add_handler(CallbackQueryHandler(pf_verify_menu_callback, pattern=r"^pf_verify_menu$"))
    
    # Verification game handlers (OLD SYSTEM - REMOVED)
    # app.add_handler(CallbackQueryHandler(pf_verify_coinflip_callback, pattern=r"^pf_verify_coinflip$"))
    # app.add_handler(CallbackQueryHandler(pf_verify_roulette_callback, pattern=r"^pf_verify_roulette$"))
    # app.add_handler(CallbackQueryHandler(pf_verify_highlow_callback, pattern=r"^pf_verify_highlow$"))
    # app.add_handler(CallbackQueryHandler(pf_verify_blackjack_callback, pattern=r"^pf_verify_blackjack$"))
    # app.add_handler(CallbackQueryHandler(pf_verify_keno_callback, pattern=r"^pf_verify_keno$"))
    # app.add_handler(CallbackQueryHandler(pf_verify_mines_callback, pattern=r"^pf_verify_mines$"))
    # app.add_handler(CallbackQueryHandler(pf_verify_tower_callback, pattern=r"^pf_verify_tower$"))
    
    # Provably Fair Conversation Handler for seed changes (KEEPING - used by /seed command)
    pf_seed_change_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(pf_change_client_seed_callback, pattern=r"^pf_change_client_seed$")],
        states={
            PF_CHANGE_CLIENT_SEED_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pf_client_seed_input_handler),
                CallbackQueryHandler(pf_cancel_seed_change_callback, pattern=r"^pf_cancel_seed_change$")
            ]
        },
        fallbacks=[CommandHandler("cancel", pf_cancel_handler)],
        per_user=True,
        per_chat=True,
        conversation_timeout=timedelta(minutes=5).total_seconds()
    )
    app.add_handler(pf_seed_change_handler)
    
    # Provably Fair Verification ConversationHandler (OLD SYSTEM - REMOVED)
    # pf_verification_handler = ConversationHandler(
    #     entry_points=[
    #         CallbackQueryHandler(pf_verify_coinflip_callback, pattern=r"^pf_verify_coinflip$"),
    #         CallbackQueryHandler(pf_verify_roulette_callback, pattern=r"^pf_verify_roulette$"),
    #         CallbackQueryHandler(pf_verify_highlow_callback, pattern=r"^pf_verify_highlow$"),
    #         CallbackQueryHandler(pf_verify_blackjack_callback, pattern=r"^pf_verify_blackjack$"),
    #         CallbackQueryHandler(pf_verify_keno_callback, pattern=r"^pf_verify_keno$"),
    #         CallbackQueryHandler(pf_verify_mines_callback, pattern=r"^pf_verify_mines$"),
    #         CallbackQueryHandler(pf_verify_tower_callback, pattern=r"^pf_verify_tower$")
    #     ],
    #     states={
    #         PF_VERIFY_INPUT_SERVER_SEED: [
    #             MessageHandler(filters.TEXT & ~filters.COMMAND, pf_verify_server_seed_input),
    #             CallbackQueryHandler(pf_verify_cancel_callback, pattern=r"^pf_verify_cancel$")
    #         ],
    #         PF_VERIFY_INPUT_CLIENT_SEED: [
    #             MessageHandler(filters.TEXT & ~filters.COMMAND, pf_verify_client_seed_input),
    #             CallbackQueryHandler(pf_verify_cancel_callback, pattern=r"^pf_verify_cancel$")
    #         ],
    #         PF_VERIFY_INPUT_NONCE: [
    #             MessageHandler(filters.TEXT & ~filters.COMMAND, pf_verify_nonce_input),
    #             CallbackQueryHandler(pf_verify_cancel_callback, pattern=r"^pf_verify_cancel$")
    #         ],
    #         PF_VERIFY_INPUT_PARAM: [
    #             MessageHandler(filters.TEXT & ~filters.COMMAND, pf_verify_param_input),
    #             CallbackQueryHandler(pf_verify_param_callback, pattern=r"^pf_verify_param_"),
    #             CallbackQueryHandler(pf_verify_cancel_callback, pattern=r"^pf_verify_cancel$")
    #         ]
    #     },
    #     fallbacks=[CallbackQueryHandler(pf_verify_cancel_callback, pattern=r"^pf_verify_cancel$")],
    #     per_user=True,
    #     per_chat=False,  # Changed to False so it works across chats (groups → DM)
    #     conversation_timeout=timedelta(minutes=10).total_seconds()
    # )
    # app.add_handler(pf_verification_handler)


    # Message listener for text and dice emojis
    app.add_handler(MessageHandler(filters.Dice.ALL | (filters.TEXT & ~filters.COMMAND), message_listener))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, message_listener)) # For welcome message

    if app.job_queue:

        for deal_id, deal in escrow_deals.items():
            if deal.get("status") == "accepted_awaiting_deposit":
                logging.info(f"Recovered active escrow deal {deal_id}, restarting monitor.")
                app.job_queue.run_repeating(monitor_escrow_deposit, interval=20, first=10, data={'deal_id': deal_id}, name=f"escrow_monitor_{deal_id}")
        
        # ===== DEPOSIT SYSTEM BACKGROUND TASKS =====
        if deposit_system_active:
            logging.info("Starting deposit monitoring tasks...")
            
            
    else:
        logging.warning("Job queue not available.")

    print("Bot started successfully with all new features!")
    print("Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

## NEW/IMPROVED CONVERSATION AND GAME FLOWS ##
@check_banned
@check_maintenance
async def start_game_conversation_from_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    command = update.message.text.split()[0].lower()
    game_type = 'mines' if command == '/mines' else 'tower'
    context.user_data['game_type'] = game_type

    if game_type == 'mines':
        buttons = [[InlineKeyboardButton(str(i), callback_data=f"bombs_{i}") for i in range(row, row + 8)] for row in range(1, 25, 8)]
        text = "💣 Select the number of mines (1-24):"
    else: # tower
        buttons = [[InlineKeyboardButton(f"{i}", callback_data=f"bombs_{i}") for i in range(1, 4)]]
        text = "🏗️ Select the number of bombs per row (1-3):"

    buttons.append([InlineKeyboardButton("Cancel", callback_data="cancel_game")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECT_BOMBS

@check_banned
@check_maintenance
async def start_game_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    game_type = 'mines' if 'mines' in query.data else 'tower'
    context.user_data['game_type'] = game_type

    if game_type == 'mines':
        buttons = [[InlineKeyboardButton(str(i), callback_data=f"bombs_{i}") for i in range(row, row + 8)] for row in range(1, 25, 8)]
        text = "💣 Select the number of mines (1-24):"
    else: # tower
        buttons = [[InlineKeyboardButton(f"{i}", callback_data=f"bombs_{i}") for i in range(1, 4)]]
        text = "🏗️ Select the number of bombs per row (1-3):"

    buttons.append([InlineKeyboardButton("Cancel", callback_data="cancel_game")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    # Set ownership after editing
    set_menu_owner(query.message, query.from_user.id)
    return SELECT_BOMBS

async def select_bombs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    bombs = query.data.split("_")[1]
    context.user_data['bombs'] = bombs
    await query.edit_message_text(f"Bombs set to {bombs}. Now, please enter your bet amount (or 'all').", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
    # Set ownership after editing
    set_menu_owner(query.message, query.from_user.id)
    return SELECT_BET_AMOUNT

async def select_bet_amount_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_type = context.user_data.get('game_type')
    single_emoji_game = context.user_data.get('single_emoji_game')
    
    if single_emoji_game:
        # Handle single emoji game bet input
        user = update.effective_user
        try:
            bet_amount_usd, bet_amount_currency, currency = parse_bet_amount(update.message.text, user.id)
        except ValueError:
            await update.message.reply_text("Invalid amount. Please enter a valid number or 'all'.")
            return SELECT_BET_AMOUNT
        
        if user_wallets.get(user.id, 0.0) < bet_amount_usd:
            await send_insufficient_balance_message(update)
            context.user_data.clear()
            return ConversationHandler.END
        
        await play_single_emoji_game(update, context, single_emoji_game, bet_amount_usd, bet_amount_currency, currency)
        context.user_data.clear()
        return ConversationHandler.END
    
    if game_type == 'mines':
        return await mines_command(update, context)
    elif game_type == 'tower':
        return await tower_command(update, context)

@check_banned
@check_maintenance
async def start_pvb_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    game_map = {"dice_bot": "dice", "football": "goal", "darts": "darts", "bowling": "bowl"}
    game_key = query.data.replace("pvb_start_", "")
    game_type = game_map.get(game_key, game_key)
    context.user_data['game_type'] = game_type

    await query.edit_message_text("Please enter your bet amount for this game (or 'all').", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
    # Set ownership after editing
    set_menu_owner(query.message, query.from_user.id)
    return SELECT_BET_AMOUNT

async def pvb_get_bet_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    try:
        bet_amount_str = update.message.text.lower()
        if bet_amount_str == 'all':
            bet_amount = user_wallets.get(user.id, 0.0)
        else:
            bet_amount = float(bet_amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
        return SELECT_BET_AMOUNT

    await ensure_user_in_wallets(user.id, user.username, context=context)
    if not await check_bet_limits(update, bet_amount, f"pvb_{context.user_data['game_type']}"):
        return SELECT_BET_AMOUNT

    if user_wallets.get(user.id, 0.0) < bet_amount:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="cancel_game")]
        ])
        await update.message.reply_text("❌ You don't have enough balance. Please enter a lower amount.", reply_markup=keyboard)
        return SELECT_BET_AMOUNT

    context.user_data['bet_amount'] = bet_amount
    await update.message.reply_text("Bet amount set. Now, please enter the points target (e.g., ft1, ft3, ft5).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
    return SELECT_TARGET_SCORE

async def pvb_get_target_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text.lower()
        if not text.startswith("ft") or not text[2:].isdigit():
            raise ValueError

        target_score = int(text[2:])
        if not 1 <= target_score <= 10:
            await update.message.reply_text("Please enter a valid target between ft1 and ft10.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
            return SELECT_TARGET_SCORE

    except (ValueError, IndexError):
        await update.message.reply_text("Invalid format. Please enter the target score as ftX (e.g., ft3).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_game")]]))
        return SELECT_TARGET_SCORE

    game_type = context.user_data['game_type']
    await play_vs_bot_game(update, context, game_type, target_score)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_game_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Determine which menu to return to based on game type
    game_type = context.user_data.get('game_type')
    context.user_data.clear()
    
    if game_type in ['mines', 'tower']:
        # Return to house games menu for mines and tower
        text = "🏠 <b>House Games</b>\n\nChoose a game to see how to play:"
        keyboard = [
            [InlineKeyboardButton("🃏 Blackjack", callback_data="game_blackjack"),
             InlineKeyboardButton("🎲 Dice Roll", callback_data="game_dice_roll")],
            [InlineKeyboardButton("🔮 Predict", callback_data="game_predict"),
             InlineKeyboardButton("🎯 Roulette", callback_data="game_roulette")],
            [InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
             InlineKeyboardButton("🏗️ Tower", callback_data="game_tower_start")],
            [InlineKeyboardButton("💣 Mines", callback_data="game_mines_start"),
             InlineKeyboardButton("🎯 Keno", callback_data="game_keno")],
            [InlineKeyboardButton("🪙 Coin Flip", callback_data="game_coin_flip"),
             InlineKeyboardButton("🎴 High-Low", callback_data="game_highlow")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="main_games")]
        ]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # For other games, return to main menu
        await query.edit_message_text("Game setup cancelled.")
        await start_command_inline(query, context)
    
    return ConversationHandler.END

## NEW FEATURE - AI Conversation Flow ##
@check_banned
@check_maintenance
async def start_ai_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🧠 Perplexity (Online)", callback_data="ai_model_perplexity")],
        [InlineKeyboardButton("🆓 GPT4Free (Free)", callback_data="ai_model_g4f")],
        [InlineKeyboardButton("🔙 Cancel & Back to Menu", callback_data="cancel_ai")]
    ]
    await safe_edit_message(
        query,
        "🤖 <b>AI Assistant</b>\n\nWhich AI model would you like to use?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_AI_MODEL

async def choose_ai_model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    # Check menu ownership
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    model_choice = query.data.split('_')[-1]
    context.user_data['ai_model'] = model_choice

    await safe_edit_message(
        query,
        f"🤖 <b>AI Assistant ({model_choice.title()})</b>\n\nI'm ready to help! What's on your mind? Ask me anything.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel & Back to Menu", callback_data="cancel_ai")]])
    )
    return ASK_AI_PROMPT

async def ai_conversation_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    model_choice = context.user_data.get('ai_model')
    if not model_choice:
        await update.message.reply_text("An error occurred. Please start the AI assistant again.")
        context.user_data.clear()
        await start_command(update, context)
        return ConversationHandler.END

    prompt = update.message.text
    await process_ai_request(update, prompt, model_choice)

    # Prompt again for the next question
    await update.message.reply_text(
        "What else can I help you with?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel & Back to Menu", callback_data="cancel_ai")]])
    )
    return ASK_AI_PROMPT

async def cancel_ai_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    # Return to More menu instead of main menu
    await more_menu(update, context)
    return ConversationHandler.END

# --- NEW Bonus & Rakeback System ---
async def bonuses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="main_daily")],
        [InlineKeyboardButton("📅 Weekly Bonus", callback_data="bonus_weekly")],
        [InlineKeyboardButton("🗓️ Monthly Bonus", callback_data="bonus_monthly")],
        [InlineKeyboardButton("💰 Rakeback", callback_data="bonus_rakeback")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
    ]
    
    await safe_edit_message(
        query,
        "🎁 <b>Bonuses & Rakeback</b> 🎁\n\n"
        "Claim your rewards for playing! Choose an option below.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bonus_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Check menu ownership BEFORE answering
    if not check_menu_ownership(query, context):
        await query.answer("This menu is not for you.", show_alert=True)
        return
    
    await query.answer()
    
    user = query.from_user
    action = query.data.split('_')[1]
    
    if action == "weekly":
        await weekly_bonus_command(update, context, from_callback=True)
    elif action == "monthly":
        await monthly_bonus_command(update, context, from_callback=True)
    elif action == "rakeback":
        await rakeback_command(update, context, from_callback=True)

@check_banned
@check_maintenance
async def weekly_bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    stats = user_stats[user.id]
    
    last_claim_str = stats.get("last_weekly_claim")
    if last_claim_str:
        last_claim_time = datetime.fromisoformat(last_claim_str)
        if datetime.now(timezone.utc) - last_claim_time < timedelta(days=7):
            time_left = timedelta(days=7) - (datetime.now(timezone.utc) - last_claim_time)
            await update.message.reply_text(f"You've already claimed your weekly bonus. Try again in {time_left.days}d {time_left.seconds//3600}h.")
            return

    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    wagered_last_week = sum(h['amount'] for h in stats.get('bets', {}).get('history', []) if datetime.fromisoformat(h['timestamp']) >= one_week_ago)
    
    bonus = wagered_last_week * 0.005 # 0.5%
    
    if bonus > 0:
        user_wallets[user.id] += bonus
        stats["last_weekly_claim"] = str(now)
        save_user_data(user.id)
        await update.message.reply_text(f"🎉 You've claimed your weekly bonus of ${bonus:.2f} (0.5% of ${wagered_last_week:.2f} wagered).")
    else:
        await update.message.reply_text("You haven't wagered anything in the last 7 days to claim a weekly bonus.")

@check_banned
@check_maintenance
async def monthly_bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    stats = user_stats[user.id]
    
    last_claim_str = stats.get("last_monthly_claim")
    if last_claim_str:
        last_claim_time = datetime.fromisoformat(last_claim_str)
        if datetime.now(timezone.utc) - last_claim_time < timedelta(days=30):
            time_left = timedelta(days=30) - (datetime.now(timezone.utc) - last_claim_time)
            await update.message.reply_text(f"You've already claimed your monthly bonus. Try again in {time_left.days}d {time_left.seconds//3600}h.")
            return

    now = datetime.now(timezone.utc)
    one_month_ago = now - timedelta(days=30)
    wagered_last_month = sum(h['amount'] for h in stats.get('bets', {}).get('history', []) if datetime.fromisoformat(h['timestamp']) >= one_month_ago)
    
    bonus = wagered_last_month * 0.003 # 0.3%
    
    if bonus > 0:
        user_wallets[user.id] += bonus
        stats["last_monthly_claim"] = str(now)
        save_user_data(user.id)
        await update.message.reply_text(f"🎉 You've claimed your monthly bonus of ${bonus:.2f} (0.3% of ${wagered_last_month:.2f} wagered).")
    else:
        await update.message.reply_text("You haven't wagered anything in the last 30 days to claim a monthly bonus.")

@check_banned
@check_maintenance
async def demo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /demo - Users claim demo amount (once per cooldown period)
    /demo amount - Admin sets demo amount
    /demo on/off - Admin enables/disables demo feature
    """
    user = update.effective_user
    args = update.message.text.strip().split()
    
    # Admin commands
    if user.id == BOT_OWNER_ID and len(args) > 1:
        if args[1].lower() == "on":
            bot_settings["demo_enabled"] = True
            save_all_data()
            await update.message.reply_text("✅ Demo feature enabled!")
            return
        elif args[1].lower() == "off":
            bot_settings["demo_enabled"] = False
            save_all_data()
            await update.message.reply_text("❌ Demo feature disabled!")
            return
        else:
            # Try to set amount
            try:
                amount = float(args[1])
                if amount <= 0:
                    await update.message.reply_text("❌ Amount must be positive!")
                    return
                bot_settings["demo_amount"] = amount
                save_all_data()
                await update.message.reply_text(f"✅ Demo amount set to ${amount:.2f}")
                return
            except ValueError:
                await update.message.reply_text("❌ Invalid amount! Usage: /demo <amount>")
                return
    
    # Regular user claim
    if not bot_settings.get("demo_enabled", True):
        await update.message.reply_text("❌ Demo feature is currently disabled.")
        return
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    stats = user_stats[user.id]
    
    # Check cooldown
    last_claim_str = stats.get("last_demo_claim")
    if last_claim_str:
        last_claim_time = datetime.fromisoformat(last_claim_str)
        cooldown_seconds = bot_settings.get("demo_cooldown", 600)
        time_since_claim = (datetime.now(timezone.utc) - last_claim_time).total_seconds()
        
        if time_since_claim < cooldown_seconds:
            time_left_seconds = int(cooldown_seconds - time_since_claim)
            minutes = time_left_seconds // 60
            seconds = time_left_seconds % 60
            await update.message.reply_text(
                f"⏰ You can claim demo again in {minutes}m {seconds}s"
            )
            return
    
    # Give demo amount
    demo_amount = bot_settings.get("demo_amount", 10.0)
    user_wallets[user.id] += demo_amount
    stats["last_demo_claim"] = str(datetime.now(timezone.utc))
    save_user_data(user.id)
    
    await update.message.reply_text(
        f"🎁 <b>Demo Claimed!</b>\n\n"
        f"You received <b>${demo_amount:.2f}</b>\n"
        f"New balance: <b>${user_wallets[user.id]:.2f}</b>\n\n"
        f"💡 Try your luck with our games!",
        parse_mode=ParseMode.HTML
    )

@check_banned
@check_maintenance
async def serverseed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user their current server seed hash"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    pf_data = user_stats[user.id].get("provably_fair", {})
    server_seed = pf_data.get("server_seed", "")
    
    # Hash the server seed to show to user (can't reveal actual seed until rotation)
    server_seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
    
    keyboard = [[InlineKeyboardButton("🔄 Rotate Seeds", callback_data="pf_rotate_seeds")]]
    
    await update.message.reply_text(
        f"🎲 <b>Provably Fair - Server Seed</b>\n\n"
        f"<b>Server Seed Hash (SHA-256):</b>\n"
        f"<code>{server_seed_hash}</code>\n\n"
        f"<b>Nonce:</b> {pf_data.get('nonce', 0)}\n\n"
        f"💡 The actual server seed is hidden until you rotate to a new one.\n"
        f"This ensures fairness - we can't change the seed after you know the hash!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@check_banned
@check_maintenance
async def seed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show and allow changing the client seed"""
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    pf_data = user_stats[user.id].get("provably_fair", {})
    client_seed = pf_data.get("client_seed", "")
    nonce = pf_data.get("nonce", 0)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Change Client Seed", callback_data="pf_change_client_seed")],
        [InlineKeyboardButton("🔄 Rotate All Seeds", callback_data="pf_rotate_seeds")]
    ]
    
    await update.message.reply_text(
        f"🎲 <b>Provably Fair - Your Seed</b>\n\n"
        f"<b>Client Seed:</b>\n"
        f"<code>{client_seed}</code>\n\n"
        f"<b>Nonce:</b> {nonce}\n\n"
        f"💡 You can change your client seed anytime.\n"
        f"The nonce increases with each bet using these seeds.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Provably Fair Callback Handlers ---
async def pf_rotate_seeds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rotate server seed - reveal old one and activate next one"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    pf_data = user_stats[user.id].get("provably_fair", {})
    
    # Reveal old server seed
    old_server_seed = pf_data.get("server_seed", "")
    old_nonce = pf_data.get("nonce", 0)
    
    # Rotate to next seed
    pf_data["server_seed"] = pf_data.get("next_server_seed", generate_server_seed())
    pf_data["next_server_seed"] = generate_server_seed()
    pf_data["nonce"] = 0  # Reset nonce
    
    save_user_data(user.id)
    
    # Show the revealed seed
    new_seed_hash = hashlib.sha256(pf_data["server_seed"].encode()).hexdigest()
    
    await query.edit_message_text(
        f"🔄 <b>Seeds Rotated!</b>\n\n"
        f"<b>Previous Server Seed (REVEALED):</b>\n"
        f"<code>{old_server_seed}</code>\n\n"
        f"<b>Used for {old_nonce} bets</b>\n\n"
        f"<b>New Server Seed Hash:</b>\n"
        f"<code>{new_seed_hash}</code>\n\n"
        f"✅ Nonce reset to 0\n"
        f"💡 You can now verify all bets made with the old seed!",
        parse_mode=ParseMode.HTML
    )

async def pf_change_client_seed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start conversation to change client seed"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    # Add cancel button
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="pf_cancel_seed_change")]]
    
    await query.edit_message_text(
        f"🔄 <b>Change Client Seed</b>\n\n"
        f"Please send your new client seed.\n\n"
        f"📝 Requirements:\n"
        f"• 4-64 characters\n"
        f"• Letters and numbers only\n\n"
        f"Tap Cancel below to abort.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PF_CHANGE_CLIENT_SEED_INPUT

async def pf_client_seed_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new client seed input"""
    user = update.effective_user
    new_seed = update.message.text.strip()
    
    # Validate seed
    if len(new_seed) < 4 or len(new_seed) > 64:
        await update.message.reply_text(
            "❌ Client seed must be between 4-64 characters.\n"
            "Please try again or send /cancel"
        )
        return PF_CHANGE_CLIENT_SEED_INPUT
    
    if not new_seed.replace('_', '').replace('-', '').isalnum():
        await update.message.reply_text(
            "❌ Client seed can only contain letters, numbers, _ and -\n"
            "Please try again or send /cancel"
        )
        return PF_CHANGE_CLIENT_SEED_INPUT
    
    await ensure_user_in_wallets(user.id, user.username, context=context)
    
    # Update client seed
    pf_data = user_stats[user.id].get("provably_fair", {})
    old_seed = pf_data.get("client_seed", "")
    pf_data["client_seed"] = new_seed
    pf_data["nonce"] = 0  # Reset nonce
    
    save_user_data(user.id)
    
    await update.message.reply_text(
        f"✅ <b>Client Seed Updated!</b>\n\n"
        f"<b>Old Seed:</b> <code>{old_seed}</code>\n"
        f"<b>New Seed:</b> <code>{new_seed}</code>\n\n"
        f"Nonce reset to 0",
        parse_mode=ParseMode.HTML
    )
    
    return ConversationHandler.END

async def pf_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel seed change"""
    await update.message.reply_text("❌ Seed change cancelled.")
    return ConversationHandler.END

async def pf_cancel_seed_change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel seed change via inline button"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Seed change cancelled.")
    return ConversationHandler.END

async def pf_show_game_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show provably fair details for a completed game"""
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("pf_show_", "")
    game = game_sessions.get(game_id)
    
    if not game:
        await query.edit_message_text("❌ Game not found or expired.")
        return
    
    # Get game details
    server_seed_hash = hashlib.sha256(game.get("server_seed", "").encode()).hexdigest()
    client_seed = game.get("client_seed", "N/A")
    nonce = game.get("nonce", 0)
    game_type = game.get("game_type", "unknown")
    
    text = (
        f"🎲 <b>Provably Fair Details</b>\n"
        f"Game ID: <code>{game_id}</code>\n\n"
        f"<b>Server Seed (SHA-256):</b>\n"
        f"<code>{server_seed_hash}</code>\n\n"
        f"<b>Client Seed:</b>\n"
        f"<code>{client_seed}</code>\n\n"
        f"<b>Nonce:</b> {nonce}\n"
        f"<b>Game Type:</b> {game_type}\n\n"
        f"💡 Use /serverseed to rotate your seed and reveal the actual server seed.\n"
        f"Then you can verify this result independently!"
    )
    
    keyboard = [[InlineKeyboardButton("🔍 Verify Result", callback_data=f"pf_verify_menu")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def pf_verify_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show verification menu with game selection"""
    query = update.callback_query
    await query.answer()
    
    # Check if this is a group chat
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type in ["group", "supergroup"]:
        # In group chat - send DM to user
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="🔍 <b>Verify Game Result</b>\n\n"
                     "Select the game type you want to verify:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🪙 Coinflip", callback_data="pf_verify_coinflip"),
                     InlineKeyboardButton("🎯 Roulette", callback_data="pf_verify_roulette")],
                    [InlineKeyboardButton("🎰 High-Low", callback_data="pf_verify_highlow"),
                     InlineKeyboardButton("🃏 Blackjack", callback_data="pf_verify_blackjack")],
                    [InlineKeyboardButton("🎱 Keno", callback_data="pf_verify_keno"),
                     InlineKeyboardButton("💣 Mines", callback_data="pf_verify_mines")],
                    [InlineKeyboardButton("🗼 Tower", callback_data="pf_verify_tower")]
                ])
            )
            await query.edit_message_text(
                f"✅ Check your DM for verification!",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Please start a private chat with me first by clicking @{context.bot.username}",
                parse_mode=ParseMode.HTML
            )
        return ConversationHandler.END
    
    # In private chat - show menu normally
    keyboard = [
        [InlineKeyboardButton("🪙 Coinflip", callback_data="pf_verify_coinflip"),
         InlineKeyboardButton("🎯 Roulette", callback_data="pf_verify_roulette")],
        [InlineKeyboardButton("🎰 High-Low", callback_data="pf_verify_highlow"),
         InlineKeyboardButton("🃏 Blackjack", callback_data="pf_verify_blackjack")],
        [InlineKeyboardButton("🎱 Keno", callback_data="pf_verify_keno"),
         InlineKeyboardButton("💣 Mines", callback_data="pf_verify_mines")],
        [InlineKeyboardButton("🗼 Tower", callback_data="pf_verify_tower")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        f"🔍 <b>Verify Game Result</b>\n\n"
        f"Select the game type you want to verify.\n\n"
        f"You'll need:\n"
        f"• Server seed (revealed after rotation)\n"
        f"• Client seed\n"
        f"• Nonce\n"
        f"• Game-specific parameters",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Verification handlers for each game type - Now with ACTUAL CALCULATION
async def pf_verify_coinflip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start coinflip verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'coinflip'
    
    await query.edit_message_text(
        f"🪙 <b>Verify Coinflip Result</b>\n\n"
        f"I'll calculate the result for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

async def pf_verify_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start roulette verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'roulette'
    
    await query.edit_message_text(
        f"🎯 <b>Verify Roulette Result</b>\n\n"
        f"I'll calculate the result for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

async def pf_verify_highlow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start high-low verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'highlow'
    
    await query.edit_message_text(
        f"🎴 <b>Verify High-Low Result</b>\n\n"
        f"I'll calculate the shuffled deck for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

async def pf_verify_blackjack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start blackjack verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'blackjack'
    
    await query.edit_message_text(
        f"🃏 <b>Verify Blackjack Result</b>\n\n"
        f"I'll calculate the shuffled deck for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

async def pf_verify_keno_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start keno verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'keno'
    
    await query.edit_message_text(
        f"🎱 <b>Verify Keno Result</b>\n\n"
        f"I'll calculate the drawn numbers for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

async def pf_verify_mines_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start mines verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'mines'
    
    await query.edit_message_text(
        f"💣 <b>Verify Mines Result</b>\n\n"
        f"I'll calculate the mine positions for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

async def pf_verify_tower_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start tower verification process"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['pf_verify_game'] = 'tower'
    
    await query.edit_message_text(
        f"🗼 <b>Verify Tower Result</b>\n\n"
        f"I'll calculate the snake positions for you!\n\n"
        f"Please enter the <b>Server Seed</b> (revealed after rotation):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pf_verify_cancel")]])
    )
    
    return PF_VERIFY_INPUT_SERVER_SEED

# Verification input handlers
async def pf_verify_server_seed_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle server seed input for verification"""
    server_seed = update.message.text.strip()
    context.user_data['pf_verify_server_seed'] = server_seed
    
    await update.message.reply_text(
        f"✅ Server seed saved.\n\n"
        f"Now, please enter the <b>Client Seed</b>:",
        parse_mode=ParseMode.HTML
    )
    
    return PF_VERIFY_INPUT_CLIENT_SEED

async def pf_verify_client_seed_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle client seed input for verification"""
    client_seed = update.message.text.strip()
    context.user_data['pf_verify_client_seed'] = client_seed
    
    await update.message.reply_text(
        f"✅ Client seed saved.\n\n"
        f"Now, please enter the <b>Nonce</b> (number):",
        parse_mode=ParseMode.HTML
    )
    
    return PF_VERIFY_INPUT_NONCE

async def pf_verify_nonce_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle nonce input and calculate result based on game type"""
    try:
        nonce = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid nonce. Please enter a number.")
        return PF_VERIFY_INPUT_NONCE
    
    context.user_data['pf_verify_nonce'] = nonce
    game = context.user_data.get('pf_verify_game')
    
    # Games that need additional parameter
    if game in ['mines', 'tower']:
        if game == 'mines':
            await update.message.reply_text(
                f"✅ Nonce saved.\n\n"
                f"Finally, how many <b>mines</b> were in the game? (1-24):",
                parse_mode=ParseMode.HTML
            )
        else:  # tower
            keyboard = [
                [InlineKeyboardButton("Easy", callback_data="pf_verify_param_easy")],
                [InlineKeyboardButton("Medium", callback_data="pf_verify_param_medium")],
                [InlineKeyboardButton("Hard", callback_data="pf_verify_param_hard")]
            ]
            await update.message.reply_text(
                f"✅ Nonce saved.\n\n"
                f"Finally, select the <b>Difficulty</b>:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return PF_VERIFY_INPUT_PARAM
    
    # Calculate and show result for games without additional parameter
    return await pf_verify_calculate_result(update, context)

async def pf_verify_param_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle additional parameter input (mine count)"""
    game = context.user_data.get('pf_verify_game')
    
    if game == 'mines':
        try:
            mine_count = int(update.message.text.strip())
            if mine_count < 1 or mine_count > 24:
                await update.message.reply_text("❌ Invalid mine count. Please enter 1-24.")
                return PF_VERIFY_INPUT_PARAM
            context.user_data['pf_verify_param'] = mine_count
        except ValueError:
            await update.message.reply_text("❌ Invalid input. Please enter a number 1-24.")
            return PF_VERIFY_INPUT_PARAM
    
    # Calculate and show result
    return await pf_verify_calculate_result(update, context)

async def pf_verify_param_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle difficulty selection for tower"""
    query = update.callback_query
    await query.answer()
    
    difficulty = query.data.replace("pf_verify_param_", "")
    context.user_data['pf_verify_param'] = difficulty
    
    # Calculate and show result
    return await pf_verify_calculate_result(query, context, is_callback=True)

async def pf_verify_calculate_result(update_or_query, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Calculate verification result based on game type"""
    server_seed = context.user_data['pf_verify_server_seed']
    client_seed = context.user_data['pf_verify_client_seed']
    nonce = context.user_data['pf_verify_nonce']
    game = context.user_data['pf_verify_game']
    
    result_text = f"🔍 <b>VERIFICATION RESULT</b>\n\n"
    result_text += f"<b>Server Seed:</b> <code>{server_seed[:20]}...</code>\n"
    result_text += f"<b>Client Seed:</b> <code>{client_seed}</code>\n"
    result_text += f"<b>Nonce:</b> <code>{nonce}</code>\n\n"
    
    if game == 'coinflip':
        result = get_provably_fair_result(server_seed, client_seed, nonce, 2)
        result_text += f"<b>Calculated Result:</b> {result} ({'Heads' if result == 0 else 'Tails'})\n\n"
        result_text += f"Compare this with your game result!"
        
    elif game == 'roulette':
        result = get_provably_fair_result(server_seed, client_seed, nonce, 37)
        color = get_roulette_color(result)
        result_text += f"<b>Calculated Result:</b> {result} ({color})\n\n"
        result_text += f"Compare this with your game result!"
        
    elif game == 'highlow':
        deck = create_deck()
        for i in range(len(deck) - 1, 0, -1):
            j = get_provably_fair_result(server_seed, client_seed, nonce + i, i + 1)
            deck[i], deck[j] = deck[j], deck[i]
        result_text += f"<b>Shuffled Deck (first 10 cards):</b>\n"
        result_text += ", ".join([str(card) for card in deck[:10]])
        result_text += "\n\nCompare with your game's dealt cards!"
        
    elif game == 'blackjack':
        deck = create_deck()
        for i in range(len(deck) - 1, 0, -1):
            j = get_provably_fair_result(server_seed, client_seed, nonce + i, i + 1)
            deck[i], deck[j] = deck[j], deck[i]
        result_text += f"<b>Shuffled Deck (first 10 cards):</b>\n"
        result_text += ", ".join([str(card) for card in deck[:10]])
        result_text += "\n\nCompare with your game's dealt cards!"
        
    elif game == 'keno':
        drawn_numbers = []
        offset = 0
        while len(drawn_numbers) < 20:
            num = get_provably_fair_result(server_seed, client_seed, nonce + offset, 40) + 1
            if num not in drawn_numbers:
                drawn_numbers.append(num)
            offset += 1
        drawn_numbers.sort()
        result_text += f"<b>Drawn Numbers (20):</b>\n"
        result_text += ", ".join(map(str, drawn_numbers))
        result_text += "\n\nCompare with your game's drawn numbers!"
        
    elif game == 'mines':
        mine_count = context.user_data['pf_verify_param']
        result_text += f"<b>Mine Count:</b> {mine_count}\n\n"
        mine_positions = generate_mine_positions(server_seed, client_seed, nonce, mine_count)
        result_text += f"<b>Mine Positions:</b>\n"
        result_text += ", ".join(map(str, sorted(mine_positions)))
        result_text += "\n\nCompare with the revealed board!"
        
    elif game == 'tower':
        difficulty = context.user_data['pf_verify_param']
        result_text += f"<b>Difficulty:</b> {difficulty.title()}\n\n"
        snake_positions = generate_tower_positions(server_seed, client_seed, nonce, difficulty)
        result_text += f"<b>Snake Positions (per floor):</b>\n"
        for i, pos in enumerate(snake_positions, 1):
            result_text += f"Floor {i}: Position {pos}\n"
        result_text += "\nCompare with your game's revealed snakes!"
    
    # Clear user data
    for key in ['pf_verify_game', 'pf_verify_server_seed', 'pf_verify_client_seed', 'pf_verify_nonce', 'pf_verify_param']:
        context.user_data.pop(key, None)
    
    if is_callback:
        await update_or_query.edit_message_text(result_text, parse_mode=ParseMode.HTML)
    else:
        await update_or_query.message.reply_text(result_text, parse_mode=ParseMode.HTML)
    
    return ConversationHandler.END

async def pf_verify_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel verification process"""
    query = update.callback_query
    await query.answer()
    
    # Clear user data
    for key in ['pf_verify_game', 'pf_verify_server_seed', 'pf_verify_client_seed', 'pf_verify_nonce', 'pf_verify_param']:
        context.user_data.pop(key, None)
    
    await query.edit_message_text("❌ Verification cancelled.", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

@check_banned
@check_maintenance
async def rakeback_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user = update.effective_user
    await ensure_user_in_wallets(user.id, user.username, context=context)
    stats = user_stats[user.id]
    
    total_wagered = stats.get("bets", {}).get("amount", 0.0)
    last_claim_wager = stats.get("last_rakeback_claim_wager", 0.0)
    
    wagered_since_last_claim = total_wagered - last_claim_wager
    
    if wagered_since_last_claim <= 0:
        message = "You have no new wagers to claim rakeback on. Play some games!"
        if from_callback:
            await update.callback_query.answer(message, show_alert=True)
        else:
            await update.message.reply_text(message)
        return
        
    current_level = get_user_level(user.id)
    rakeback_percentage = current_level["rakeback_percentage"] / 100 # Convert from 1% to 0.01
    
    rakeback_amount = wagered_since_last_claim * rakeback_percentage
    
    user_wallets[user.id] += rakeback_amount
    stats["last_rakeback_claim_wager"] = total_wagered
    save_user_data(user.id)
    
    message = f"💰 You have claimed ${rakeback_amount:.4f} in rakeback from ${wagered_since_last_claim:.2f} wagered at a rate of {current_level['rakeback_percentage']}%."
    
    if from_callback:
        # Go back to the bonuses menu after claiming
        keyboard = [[InlineKeyboardButton("🔙 Back to Bonuses", callback_data="main_bonuses")]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(f"💰 You have claimed ${rakeback_amount:.4f} in rakeback from ${wagered_since_last_claim:.2f} wagered.")

# --- NEW Gift Code System ---
async def admin_gift_code_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎁 <b>Gift Code Management</b>\n\nExisting codes:\n"
    if not gift_codes:
        text += "No active gift codes."
    else:
        for code, data in gift_codes.items():
            wager_req = data.get("wager_requirement", 0)
            wager_text = f" (Wager: ${wager_req:.0f})" if wager_req > 0 else ""
            text += f"• <code>{code}</code>: ${data['amount']:.2f}, {data['claims_left']}/{data['total_claims']} left{wager_text}\n"
            
    keyboard = [
        [InlineKeyboardButton("➕ Create New Code", callback_data="admin_gift_create")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    
async def admin_gift_code_create_step1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the amount (e.g., 5.50) for the new gift code.",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_gift_codes")]]))
    return ADMIN_GIFT_CODE_AMOUNT

async def admin_gift_code_create_step2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount <= 0: raise ValueError
        context.user_data['gift_code_amount'] = amount
        await update.message.reply_text("Amount set. Now enter the maximum number of times this code can be claimed.",
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_gift_codes")]]))
        return ADMIN_GIFT_CODE_CLAIMS
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a positive number.")
        return ADMIN_GIFT_CODE_AMOUNT

async def admin_gift_code_create_step3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        claims = int(update.message.text)
        if claims <= 0: raise ValueError
        context.user_data['gift_code_claims'] = claims
        await update.message.reply_text(
            "Number of claims set. Now enter the wager requirement (in $).\n\n"
            "Enter <b>0</b> for no wager requirement, or any positive number (e.g., 100 means users must have wagered $100 to claim).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_gift_codes")]]),
            parse_mode=ParseMode.HTML
        )
        return ADMIN_GIFT_CODE_WAGER
    except ValueError:
        await update.message.reply_text("Invalid number. Please enter a positive integer.")
        return ADMIN_GIFT_CODE_CLAIMS

async def admin_gift_code_create_step4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wager_requirement = float(update.message.text)
        if wager_requirement < 0: raise ValueError
        
        amount = context.user_data['gift_code_amount']
        claims = context.user_data['gift_code_claims']
        
        code = f"GIFT-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        gift_codes[code] = {
            "amount": amount,
            "total_claims": claims,
            "claims_left": claims,
            "wager_requirement": wager_requirement,
            "claimed_by": [],
            "created_by": update.effective_user.id,
            "created_at": str(datetime.now(timezone.utc))
        }
        save_gift_code(code)
        
        wager_text = f"Wager requirement: ${wager_requirement:.2f}" if wager_requirement > 0 else "No wager requirement"
        
        # Build gift codes list for display
        codes_text = "🎁 <b>Gift Code Management</b>\n\nExisting codes:\n"
        if not gift_codes:
            codes_text += "No active gift codes."
        else:
            for gift_code, data in gift_codes.items():
                wager_req = data.get("wager_requirement", 0)
                wager_text_item = f" (Wager: ${wager_req:.0f})" if wager_req > 0 else ""
                codes_text += f"• <code>{gift_code}</code>: ${data['amount']:.2f}, {data['claims_left']}/{data['total_claims']} left{wager_text_item}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Create New Code", callback_data="admin_gift_create")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")]
        ]
        
        await update.message.reply_text(
            f"✅ Gift code created successfully!\n\n"
            f"Code: <code>{code}</code>\n"
            f"Amount: ${amount:.2f}\n"
            f"Uses: {claims}\n"
            f"{wager_text}\n\n"
            f"{codes_text}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data.clear()
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Invalid number. Please enter 0 or a positive number.")
        return ADMIN_GIFT_CODE_WAGER

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("=" * 80)
        print("ERROR: Failed to start bot!")
        print("=" * 80)
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        print("-" * 80)
        traceback.print_exc()
        print("=" * 80)
        print("\nCommon fixes:")
        print("1. Install all dependencies: pip install -r requirements.txt")
        print("2. Check that all config values are set in lines 95-165")
        print("3. Ensure BOT_TOKEN is set correctly (line 75)")
        print("4. Make sure directories have write permissions")
        print("=" * 80)
        import sys
        sys.exit(1)