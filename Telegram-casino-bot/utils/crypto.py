"""
Cryptographic utilities for provably fair gaming
"""
import hashlib
import random
import string
from datetime import datetime, timezone
from typing import Dict, List, Optional
from core.state import user_stats
from core.database import save_user_data

# Storage for provably fair verification records
provably_fair_records = {}

# ===== SEED GENERATION =====

def generate_server_seed() -> str:
    """Generate a random 64-character server seed"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))


def generate_client_seed() -> str:
    """Generate a random 16-character client seed"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

# ===== HASH FUNCTIONS =====

def create_hash(server_seed: str, client_seed: str, nonce: int) -> str:
    """
    Create SHA256 hash from server seed, client seed, and nonce
    This is the core of the provably fair system
    """
    combined = f"{server_seed}:{client_seed}:{nonce}"
    return hashlib.sha256(combined.encode()).hexdigest()

# ===== RESULT GENERATION =====

def get_provably_fair_result(server_seed: str, client_seed: str, nonce: int, max_value: int) -> int:
    """
    Generate a provably fair result between 0 and max_value-1
    Uses first 8 characters of the hash for randomness
    """
    hash_result = create_hash(server_seed, client_seed, nonce)
    # Convert first 8 characters of hash to integer
    hex_value = int(hash_result[:8], 16)
    return (hex_value % max_value)

# ===== SEED & NONCE MANAGEMENT =====

def get_user_seeds(user_id: int) -> Dict:
    """Get user's current seeds and nonce"""
    pf_data = user_stats.get(user_id, {}).get("provably_fair", {})
    return {
        "server_seed": pf_data.get("server_seed", generate_server_seed()),
        "client_seed": pf_data.get("client_seed", generate_client_seed()),
        "nonce": pf_data.get("nonce", 0)
    }


def increment_user_nonce(user_id: int):
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


def initialize_user_seeds(user_id: int):
    """Initialize provably fair seeds for a new user"""
    if user_id not in user_stats:
        return
    
    if "provably_fair" not in user_stats[user_id]:
        user_stats[user_id]["provably_fair"] = {
            "server_seed": generate_server_seed(),
            "client_seed": generate_client_seed(),
            "nonce": 0,
            "next_server_seed": generate_server_seed()
        }
        save_user_data(user_id)

# ===== GAME-SPECIFIC RESULT GENERATORS =====

def generate_mine_positions(server_seed: str, client_seed: str, nonce: int, num_mines: int) -> List[int]:
    """Generate deterministic mine positions for Mines game (25-tile grid)"""
    positions = []
    offset = 0
    while len(positions) < num_mines:
        pos = get_provably_fair_result(server_seed, client_seed, nonce + offset, 25)
        if pos not in positions:
            positions.append(pos)
        offset += 1
    return sorted(positions)


def generate_tower_positions(server_seed: str, client_seed: str, nonce: int, difficulty: str, num_floors: int = 9) -> List[int]:
    """Generate deterministic snake positions for Tower game"""
    tiles_per_floor = {'easy': 4, 'medium': 3, 'hard': 2}.get(difficulty, 4)
    positions = []
    for floor in range(num_floors):
        snake_pos = get_provably_fair_result(server_seed, client_seed, nonce + floor, tiles_per_floor)
        positions.append(snake_pos)
    return positions


def get_limbo_multiplier(server_seed: str, client_seed: str, nonce: int) -> float:
    """Generate provably fair Limbo multiplier (1.00-1000.00 with 3% house edge)"""
    hash_result = create_hash(server_seed, client_seed, nonce)
    hex_value = int(hash_result[:13], 16)
    max_val = 16 ** 13
    normalized = hex_value / max_val
    house_edge = 0.03
    
    try:
        result = (1 - house_edge) / normalized if normalized > 0 else 1000.00
        result = max(1.00, min(1000.00, result))
        return round(result, 2)
    except:
        return 1.00

# ===== RECORD STORAGE =====

def store_provably_fair_record(game_id: str, game_type: str, server_seed: str, 
                               client_seed: str, nonce: int, result_data: Optional[Dict] = None):
    """Store provably fair verification data for completed games"""
    provably_fair_records[game_id] = {
        "game_id": game_id,
        "game_type": game_type,
        "server_seed": server_seed,
        "client_seed": client_seed,
        "nonce": nonce,
        "result_data": result_data,
        "timestamp": str(datetime.now(timezone.utc))
    }
    
    # Keep only last 1000 records to prevent memory issues
    if len(provably_fair_records) > 1000:
        oldest_key = next(iter(provably_fair_records))
        del provably_fair_records[oldest_key]


def get_provably_fair_record(game_id: str) -> Optional[Dict]:
    """Retrieve provably fair record for a game"""
    return provably_fair_records.get(game_id)
