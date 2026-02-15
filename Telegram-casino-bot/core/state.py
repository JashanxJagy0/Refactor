"""
In-memory state management for the bot
Contains all runtime data structures
"""

# ===== USER DATA =====
# Main user wallet balances (user_id -> USD balance)
user_wallets = {}

# Comprehensive user statistics and data
# Structure: {user_id: {balance, currency, language, level, ...}}
user_stats = {}

# Username to user ID mapping for quick lookups
username_to_userid = {}

# ===== GAME STATE =====
# Active game sessions (session_id -> game_data)
game_sessions = {}

# PvP game invitations
user_pending_invitations = {}

# ===== ESCROW & TRADING =====
# Active escrow deals (deal_id -> deal_data)
escrow_deals = {}

# ===== GROUP MANAGEMENT =====
# Group-specific settings (group_id -> settings)
group_settings = {}

# ===== RECOVERY & SECURITY =====
# Account recovery tokens (token -> user_data)
recovery_data = {}

# ===== GIFT CODES =====
# Gift code system (code -> code_data)
gift_codes = {}

# ===== AI CHAT CONTEXT =====
# AI conversation history (user_id -> messages)
ai_chat_contexts = {}


def initialize_user_data(user_id: int):
    """Initialize default data structure for a new user"""
    if user_id not in user_stats:
        user_stats[user_id] = {
            "balance": 0.0,
            "currency": "USD",
            "language": "en",
            "level": 0,
            "xp": 0,
            "total_wagered": 0.0,
            "total_won": 0.0,
            "total_lost": 0.0,
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "achievements": [],
            "referral_code": None,
            "referred_by": None,
            "referrals": [],
            "referral_earnings": 0.0,
            "last_daily_bonus": None,
            "last_weekly_bonus": None,
            "last_monthly_bonus": None,
            "rakeback_accumulated": 0.0,
            "created_at": None,
            "banned": False,
            "muted": False,
            "demo_used": False,
            "last_demo_time": None,
            # Provably fair
            "server_seed": None,
            "server_seed_hash": None,
            "client_seed": None,
            "nonce": 0,
            "next_server_seed": None,
            "next_server_seed_hash": None,
            # Game-specific stats
            "blackjack_stats": {"played": 0, "won": 0, "lost": 0, "push": 0},
            "roulette_stats": {"played": 0, "won": 0, "lost": 0},
            "mines_stats": {"played": 0, "won": 0, "lost": 0, "max_tiles": 0},
            "tower_stats": {"played": 0, "won": 0, "lost": 0, "max_level": 0},
            # PvP stats
            "pvp_matches": 0,
            "pvp_wins": 0,
            "pvp_losses": 0,
        }
    
    if user_id not in user_wallets:
        user_wallets[user_id] = 0.0
    
    return user_stats[user_id]


def get_user_data(user_id: int):
    """Get user data, initialize if doesn't exist"""
    if user_id not in user_stats:
        initialize_user_data(user_id)
    return user_stats[user_id]


def update_user_balance(user_id: int, amount: float):
    """Update user balance (can be positive or negative)"""
    if user_id not in user_wallets:
        user_wallets[user_id] = 0.0
    if user_id not in user_stats:
        initialize_user_data(user_id)
    
    user_wallets[user_id] += amount
    user_stats[user_id]["balance"] = user_wallets[user_id]
    
    return user_wallets[user_id]


def get_user_balance(user_id: int) -> float:
    """Get user balance"""
    if user_id not in user_wallets:
        user_wallets[user_id] = 0.0
    return user_wallets[user_id]
