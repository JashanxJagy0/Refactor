"""
Core module for bot infrastructure
"""
from core.state import (
    user_wallets, user_stats, username_to_userid, game_sessions,
    user_pending_invitations, escrow_deals, group_settings,
    recovery_data, gift_codes, ai_chat_contexts,
    initialize_user_data, get_user_data, update_user_balance, get_user_balance
)
from core.bot_settings import (
    bot_settings, get_setting, set_setting, is_maintenance_mode,
    are_withdrawals_enabled, is_demo_enabled, get_house_balance,
    update_house_balance
)
from core.database import (
    create_directories, load_all_user_data, save_user_data, save_all_user_data,
    load_bot_state, save_bot_state, load_all_escrow_deals, save_escrow_deal,
    save_all_escrow_deals, save_group_settings, load_all_group_settings,
    save_all_group_settings, save_recovery_data, load_all_recovery_data,
    save_all_recovery_data, save_gift_code, load_all_gift_codes,
    save_all_gift_codes
)

__all__ = [
    # State
    'user_wallets', 'user_stats', 'username_to_userid', 'game_sessions',
    'user_pending_invitations', 'escrow_deals', 'group_settings',
    'recovery_data', 'gift_codes', 'ai_chat_contexts',
    'initialize_user_data', 'get_user_data', 'update_user_balance', 'get_user_balance',
    # Settings
    'bot_settings', 'get_setting', 'set_setting', 'is_maintenance_mode',
    'are_withdrawals_enabled', 'is_demo_enabled', 'get_house_balance',
    'update_house_balance',
    # Database
    'create_directories', 'load_all_user_data', 'save_user_data', 'save_all_user_data',
    'load_bot_state', 'save_bot_state', 'load_all_escrow_deals', 'save_escrow_deal',
    'save_all_escrow_deals', 'save_group_settings', 'load_all_group_settings',
    'save_all_group_settings', 'save_recovery_data', 'load_all_recovery_data',
    'save_all_recovery_data', 'save_gift_code', 'load_all_gift_codes',
    'save_all_gift_codes'
]
