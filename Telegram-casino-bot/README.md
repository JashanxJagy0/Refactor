# Telegram Casino Bot - Refactored Architecture

## Overview
This is a refactored version of the Telegram Casino Bot, restructured into a modular architecture for better maintainability, scalability, and performance.

## Project Structure

```
Telegram-casino-bot/
├── main.py                      # Entry point - Run this file
├── config.py                    # Configuration constants
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
│
├── core/                        # Core infrastructure
│   ├── bot_settings.py         # Bot settings and configuration
│   ├── state.py                # In-memory data structures
│   ├── database.py             # Persistent storage operations
│   └── __init__.py
│
├── handlers/                    # Command and callback handlers
│   ├── start.py                # /start command and main menu
│   ├── callback.py             # Callback query router
│   ├── message.py              # Message handlers
│   └── __init__.py
│
├── utils/                       # Utility functions
│   ├── helpers.py              # Currency, formatting, parsing
│   ├── language.py             # Multi-language support
│   ├── crypto.py               # Provably fair system
│   ├── decorators.py           # Security decorators
│   └── __init__.py
│
├── services/                    # External service integrations
│   ├── price_service.py        # Crypto price fetching
│   ├── ai_service.py           # AI chat integration
│   ├── translate.py            # Translation service
│   └── __init__.py
│
├── features/                    # Feature modules (Phase 2 & 3)
│   ├── games/                  # Casino games
│   ├── deposits/               # Deposit system
│   ├── withdrawals/            # Withdrawal system
│   ├── admin/                  # Admin features
│   ├── bonuses/                # Bonus system
│   ├── referrals/              # Referral system
│   └── ... (more features)
│
├── wallet/                      # Blockchain wallet infrastructure
│   ├── deposits_db.py          # SQLite deposit database
│   ├── hd_wallet.py            # HD wallet management
│   ├── block_monitor.py        # Blockchain monitoring
│   └── services/               # Chain-specific services
│
├── languages/                   # Translation files
│   ├── English.txt
│   ├── hindhi.txt
│   ├── spanish.txt
│   └── ... (more languages)
│
└── data/                        # Runtime data directories
    ├── user_data/              # User account files
    ├── escrow_deals/           # Escrow transactions
    ├── group_data/             # Group settings
    └── ... (auto-created)
```

## Phase 1 Completion Status ✅

### Completed Components:
- ✅ Configuration system (config.py, .env.example)
- ✅ Core infrastructure (state management, database operations)
- ✅ Utility modules (helpers, language, crypto, decorators)
- ✅ Service modules (price, AI, translate)
- ✅ Basic handler structure (start, callback routing)
- ✅ Main entry point (main.py)

### Ready for Testing:
The bot can now start and display the main menu. Individual features (games, deposits, etc.) will be added in Phase 2 and Phase 3.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment (optional):
```bash
cp .env.example .env
# Edit .env with your actual values
```

3. Run the bot:
```bash
python main.py
```

## Key Features

### Modular Architecture
- **Separation of Concerns**: Each module has a specific responsibility
- **Easy to Maintain**: Update individual features without touching core code
- **Scalable**: Add new games/features by creating new modules

### Provably Fair System
- Cryptographic seed generation
- Transparent result verification
- Game-specific result generators

### Multi-Language Support
- 6 languages supported (English, Hindi, Spanish, Russian, French, Chinese)
- Easy to add new languages

### Secure
- User authentication and banning system
- Maintenance mode
- Admin-only commands
- Menu ownership tracking

## Development Roadmap

### Phase 1 (COMPLETED) ✅
- Core infrastructure
- Configuration management
- Utility modules
- Basic handlers

### Phase 2 (Next Session)
- House games (Mines, Blackjack, Roulette, Tower, etc.)
- Emoji games (PvP, PvB, single games)
- Game base classes and registry

### Phase 3 (Final Session)
- Deposit/withdrawal system
- Blockchain services
- Admin dashboard
- Bonus system
- Referral system
- Complete testing

## Configuration

Edit `config.py` or set environment variables:
- `BOT_TOKEN`: Your Telegram bot token
- `BOT_OWNER_ID`: Your Telegram user ID
- `MASTER_MNEMONIC`: Master wallet seed phrase
- `PERPLEXITY_API_KEY`: AI service API key
- `MEXC_API_KEY`: Exchange API key

## Data Storage

- **In-Memory**: Fast access for active sessions
- **JSON Files**: Individual user data persistence
- **SQLite**: Blockchain deposit tracking
- **State File**: Centralized bot state backup

## Contributing

This is a refactored version for improved maintainability. Each module is self-contained and documented.

## License

All rights reserved.
