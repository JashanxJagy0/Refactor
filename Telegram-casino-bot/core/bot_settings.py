"""
Bot settings and global configuration
"""

# Global bot settings that can be modified at runtime
bot_settings = {
    "daily_bonus_amount": 0.50,
    "maintenance_mode": False,
    "house_balance": 100000000000000.0,  # 100T USD
    "withdrawals_enabled": True,
    "demo_enabled": True,
    "demo_amount": 10.0,
    "demo_cooldown": 600,  # seconds (10 minutes)
    "min_withdrawal": 10.0,
    "max_withdrawal": 100000.0,
    "withdrawal_fee_percent": 0.0,  # 0% fee
    "house_edge": 0.01,  # 1% house edge for games
    "max_bet_amount": 10000.0,
    "min_bet_amount": 0.10,
    "pvp_timeout": 300,  # 5 minutes
    "escrow_fee_percent": 0.01,  # 1% escrow fee
}


def get_setting(key: str, default=None):
    """Get a bot setting by key"""
    return bot_settings.get(key, default)


def set_setting(key: str, value):
    """Set a bot setting"""
    bot_settings[key] = value


def is_maintenance_mode() -> bool:
    """Check if bot is in maintenance mode"""
    return bot_settings.get("maintenance_mode", False)


def are_withdrawals_enabled() -> bool:
    """Check if withdrawals are enabled"""
    return bot_settings.get("withdrawals_enabled", True)


def is_demo_enabled() -> bool:
    """Check if demo mode is enabled"""
    return bot_settings.get("demo_enabled", True)


def get_house_balance() -> float:
    """Get current house balance"""
    return bot_settings.get("house_balance", 0.0)


def update_house_balance(amount: float):
    """Update house balance (positive for profit, negative for payout)"""
    current = get_house_balance()
    bot_settings["house_balance"] = current + amount
    return bot_settings["house_balance"]
