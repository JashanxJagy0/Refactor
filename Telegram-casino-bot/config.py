"""
Configuration file for Telegram Casino Bot
Contains all constants and configuration settings
"""
import os

# ===== BOT CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "7956452112:AAGSZVLZz34ep8qCsLKnTRZambI67r_T3ro")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "6083286836"))
MIN_BALANCE = 0.1
DEBUG_EMOJI_GAMES = False  # Set to True to enable detailed emoji game logging

# ===== COMMUNITY LINKS =====
LINK_PORTAL = "https://t.me/escrews"
LINK_CHANNEL = "https://t.me/escrews"
LINK_CHAT = "https://t.me/playcsino"
LINK_SUPPORT = "https://t.me/jashanxjagy"

# Win Broadcast Configuration
# Can use either Channel ID or Username
# For Channel ID: Usually requires a "-100" prefix (e.g., "-1003848853417")
# For Channel Username: Use @ prefix for public channels (e.g., "@mychannel")
# Leave empty to disable win broadcasting
WIN_BROADCAST_CHANNEL_ID = ""

# ===== API KEYS =====
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "[REDACTED]")
MEXC_API_KEY = os.getenv("MEXC_API_KEY", "mx0vgltPHKyw92y4qZ")
MEXC_API_SECRET = os.getenv("MEXC_API_SECRET", "5f4f81217f514a799e4d77842bcc4a26")

# ===== ESCROW CONFIGURATION =====
ESCROW_DEPOSIT_ADDRESS = "0xdda0e87f6c1344e07cfce9cefb12f3a286a0fb38"
ESCROW_WALLET_PRIVATE_KEY = os.getenv("ESCROW_WALLET_PRIVATE_KEY", 
                                       "0bbaf8d35b64859555b1a6acc7909ac349bced46b2fcf2c8d616343fec138353")
ESCROW_DEPOSIT_NETWORK = "bsc"
ESCROW_DEPOSIT_TOKEN_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
ESCROW_DEPOSIT_TOKEN_DECIMALS = 18
REFERRAL_BET_COMMISSION_RATE = 0.001

# ===== MASTER WALLET CONFIGURATION =====
MASTER_MNEMONIC = os.getenv("MASTER_MNEMONIC", 
    "inflict police tooth diesel ladder crawl pupil daughter label cliff clip visit base marine increase pizza kiwi royal knee panther half ill habit rookie")

HOT_WALLET_PRIVATE_KEY = os.getenv("HOT_WALLET_PRIVATE_KEY", 
    "fea03d11d9993d1b357fb01ef238ab9e59457ca9c8df9fdb3c131bac8c034b93")

MASTER_WALLETS = {
    "ETH": "0x3011d124812d638c3eb4743ebe2261a2b0e47806",
    "BNB": "0x3011d124812d638c3eb4743ebe2261a2b0e47806",
    "BASE": "0x3011d124812d638c3eb4743ebe2261a2b0e47806",
    "TRON": "TDdSwtm4wz1147GbtXEmL8Ck3wDe7m95tu",
    "SOLANA": "8DKPQrMr4X9gbbmZAcJXeLx1qHicrvLjBpRZDX1S4kgC",
    "TON": "UQC2CsdJrFkX6MctJmyrfFPZZk1orq0ewjR6k2Zv7NNs8Mmi"
}

# ===== RPC ENDPOINTS =====
RPC_ENDPOINTS = {
    "ETH": "https://eth.llamarpc.com",
    "BNB": "https://bsc-dataseed.binance.org/",
    "BASE": "https://mainnet.base.org",
    "TRON": "https://api.trongrid.io",
    "SOLANA": "https://api.mainnet-beta.solana.com",
    "TON": "https://toncenter.com/api/v2/jsonRPC"
}

# ===== TOKEN CONTRACTS =====
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

# ===== DEPOSIT SETTINGS =====
MIN_DEPOSIT_USD = 10.0
SCAN_INTERVAL = 30  # seconds
SWEEP_INTERVAL = 60  # seconds

CONFIRMATIONS = {
    "ETH": 12,
    "BNB": 15,
    "BASE": 10,
    "TRON": 19,
    "SOLANA": 32,
    "TON": 5
}

GAS_AMOUNTS = {
    "ETH": 0.005,
    "BNB": 0.001,
    "BASE": 0.0005,
    "TRON": 15,
    "SOLANA": 0.001
}

BIP44_PATHS = {
    "ETH": "m/44'/60'/0'/0",
    "BNB": "m/44'/60'/0'/0",
    "BASE": "m/44'/60'/0'/0",
    "TRON": "m/44'/195'/0'/0",
    "SOLANA": "m/44'/501'/0'/0",
    "TON": "m/44'/607'/0'/0"
}

# ===== CURRENCY SYSTEM =====
CURRENCY_RATES = {
    "USD": 1.0,
    "INR": 83.12,
    "EUR": 0.92,
    "GBP": 0.79
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£"
}

# ===== LANGUAGE SYSTEM =====
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

# ===== DIRECTORY CONFIGURATION =====
# These will be created at runtime if they don't exist
DATA_DIRECTORIES = [
    "user_data",
    "escrow_deals",
    "group_data",
    "recovery_data",
    "gift_codes",
    "logs",
    "data"
]
