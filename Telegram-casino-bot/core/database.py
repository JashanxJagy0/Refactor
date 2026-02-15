"""
Persistent storage management for the bot
Handles loading and saving all data to disk
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional

# Import state from core.state
from core.state import (
    user_wallets, user_stats, username_to_userid, game_sessions,
    user_pending_invitations, escrow_deals, group_settings,
    recovery_data, gift_codes
)
from core.bot_settings import bot_settings

# Directory configuration
DATA_DIR = "user_data"
ESCROW_DIR = "escrow_deals"
LOGS_DIR = "logs"
GROUPS_DIR = "group_data"
RECOVERY_DIR = "recovery_data"
GIFT_CODE_DIR = "gift_codes"
DATA_DB_DIR = "data"
STATE_FILE = "bot_state.json"
CRYPTO_PRICES_FILE = "crypto_prices.json"

# Create directories
def create_directories():
    """Create all necessary directories"""
    directories = [
        DATA_DIR, ESCROW_DIR, LOGS_DIR, GROUPS_DIR, 
        RECOVERY_DIR, GIFT_CODE_DIR, DATA_DB_DIR
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# ===== USER DATA FUNCTIONS =====

def normalize_username(username: str) -> str:
    """Normalize username for consistent lookups"""
    if not username:
        return ""
    return username.lower().strip().lstrip("@")


def load_all_user_data():
    """Load all user data from individual JSON files"""
    global user_wallets, username_to_userid, user_stats
    
    logging.info("Loading all user data from files...")
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
    logging.info(f"Loaded data for {len(user_stats)} users.")


def save_user_data(user_id: int):
    """Save individual user data to JSON file"""
    if user_id not in user_stats:
        logging.warning(f"Attempted to save data for non-existent user: {user_id}")
        return
    
    data = user_stats.get(user_id, {})
    data["wallet"] = user_wallets.get(user_id, 0.0)
    
    try:
        with open(os.path.join(DATA_DIR, f"{user_id}.json"), "w") as f:
            json.dump(data, f, default=str, indent=2)
    except Exception as e:
        logging.error(f"Failed to save user data for {user_id}: {e}")


def save_all_user_data():
    """Save all user data to individual JSON files"""
    logging.info("Saving all user data...")
    for user_id in user_stats.keys():
        save_user_data(user_id)
    logging.info("All user data saved.")

# ===== BOT STATE FUNCTIONS =====

def save_bot_state():
    """Save the entire bot state to a single JSON file"""
    logging.info("Saving bot state...")
    state = {
        'user_wallets': user_wallets,
        'username_to_userid': username_to_userid,
        'game_sessions': game_sessions,
        'user_pending_invitations': user_pending_invitations,
        'escrow_deals': escrow_deals,
        'bot_settings': bot_settings
    }
    
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, default=str, indent=2)
        logging.info("Bot state saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save bot state: {e}")
    
    # Also save individual files as backup
    save_all_user_data()
    save_all_escrow_deals()
    save_all_group_settings()
    save_all_recovery_data()
    save_all_gift_codes()


def load_bot_state():
    """Load the bot state from JSON files"""
    global user_wallets, username_to_userid, game_sessions
    global user_pending_invitations, escrow_deals
    
    logging.info("Loading bot state...")
    
    # Load individual files first as fallback
    load_all_user_data()
    load_all_escrow_deals()
    load_all_group_settings()
    load_all_recovery_data()
    load_all_gift_codes()
    
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
            bot_settings.update(state.get('bot_settings', {}))
            
            logging.info("Bot state restored successfully from state file.")
        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"Could not load bot state from {STATE_FILE}: {e}")
    else:
        logging.info("No state file found. Starting with fresh state.")

# ===== ESCROW DEAL FUNCTIONS =====

def load_all_escrow_deals():
    """Load all escrow deals from individual JSON files"""
    global escrow_deals
    
    logging.info("Loading all escrow deals...")
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


def save_escrow_deal(deal_id: str):
    """Save individual escrow deal to JSON file"""
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
    """Save all escrow deals to individual JSON files"""
    logging.info("Saving all escrow deals...")
    for deal_id in escrow_deals.keys():
        save_escrow_deal(deal_id)
    logging.info("All escrow deals saved.")

# ===== GROUP SETTINGS FUNCTIONS =====

def save_group_settings(chat_id: int):
    """Save group settings to JSON file"""
    settings = group_settings.get(chat_id)
    if not settings:
        return
    
    try:
        with open(os.path.join(GROUPS_DIR, f"{chat_id}.json"), "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save group settings for {chat_id}: {e}")


def load_all_group_settings():
    """Load all group settings from JSON files"""
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
    """Save all group settings to JSON files"""
    logging.info("Saving all group settings...")
    for chat_id in group_settings.keys():
        save_group_settings(chat_id)
    logging.info("All group settings saved.")

# ===== RECOVERY DATA FUNCTIONS =====

def save_recovery_data(token_hash: str):
    """Save recovery data to JSON file"""
    data = recovery_data.get(token_hash)
    if not data:
        return
    
    try:
        with open(os.path.join(RECOVERY_DIR, f"{token_hash}.json"), "w") as f:
            json.dump(data, f, default=str, indent=2)
    except Exception as e:
        logging.error(f"Failed to save recovery data for token hash {token_hash}: {e}")


def load_all_recovery_data():
    """Load all recovery data from JSON files"""
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
    """Save all recovery data to JSON files"""
    logging.info("Saving all recovery data...")
    for token_hash in recovery_data.keys():
        save_recovery_data(token_hash)
    logging.info("All recovery data saved.")

# ===== GIFT CODE FUNCTIONS =====

def save_gift_code(code: str):
    """Save gift code to JSON file"""
    data = gift_codes.get(code)
    if not data:
        return
    
    try:
        with open(os.path.join(GIFT_CODE_DIR, f"{code}.json"), "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save gift code {code}: {e}")


def load_all_gift_codes():
    """Load all gift codes from JSON files"""
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
    """Save all gift codes to JSON files"""
    logging.info("Saving all gift codes...")
    for code in gift_codes.keys():
        save_gift_code(code)
    logging.info("All gift codes saved.")
