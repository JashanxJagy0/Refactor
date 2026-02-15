# 🚀 Quick Start Guide - Telegram Casino Bot

## Installation (5 minutes)

### 1. Prerequisites
```bash
# Ensure Python 3.9+ is installed
python3 --version

# Clone the repository (if not already done)
git clone <repository-url>
cd Telegram-casino-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Bot
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Configuration:**
```bash
BOT_TOKEN=your_telegram_bot_token_here
BOT_OWNER_ID=your_telegram_user_id_here
```

**Optional (for blockchain features):**
```bash
MASTER_MNEMONIC=your_12_or_24_word_mnemonic
ETHEREUM_RPC=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BNB_RPC=https://bsc-dataseed.binance.org/
# ... other blockchain RPCs
```

### 4. Run the Bot
```bash
python main.py
```

**Success!** Your bot should now be running.

---

## Getting Your Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the bot token provided
5. Paste into `.env` file as `BOT_TOKEN`

---

## Getting Your User ID

1. Open Telegram and search for [@userinfobot](https://t.me/userinfobot)
2. Start the bot
3. Copy your user ID
4. Paste into `.env` file as `BOT_OWNER_ID`

---

## First Steps After Launch

### 1. Test the Bot
- Open your bot in Telegram
- Send `/start` command
- You should see the main menu

### 2. Check Admin Access
- Send `/admin` command
- You should see the admin dashboard
- If not, verify `BOT_OWNER_ID` is correct

### 3. Test a Game
- Send `/mines 1.50 5` to play Mines
- Or click 🎮 Games button in menu

### 4. Add Demo Balance
- Send `/demo` to get $50 demo balance
- Use this to test games

---

## Common Commands

### For Users:
```
/start          - Start the bot
/balance        - Check your balance
/deposit        - Deposit crypto
/games          - View all games
/daily          - Claim daily bonus
/ref            - Get referral link
/help           - Get help
```

### For Admin (You):
```
/admin          - Admin dashboard
/users          - View all users
/addbalance     - Add user balance
/broadcast      - Message all users
/maintenance    - Toggle maintenance mode
```

### Quick Game Commands:
```
/mines 1.50 5   - Mines game ($1.50, 5 mines)
/flip 2.00      - Coin flip ($2.00)
/blackjack 5    - Blackjack ($5.00)
/roulette 1 red - Roulette ($1.00 on red)
```

---

## Project Structure

```
Telegram-casino-bot/
├── main.py              # Start here! Entry point
├── config.py            # Configuration
├── .env                 # Your secrets (create from .env.example)
│
├── core/                # Core systems
├── utils/               # Utility functions
├── services/            # External services
├── handlers/            # Command handlers
├── features/            # All features (games, admin, etc.)
├── wallet/              # Blockchain integration
└── languages/           # Translations
```

---

## Troubleshooting

### Bot doesn't start?
```bash
# Check Python version
python3 --version  # Must be 3.9+

# Check token is set
cat .env | grep BOT_TOKEN

# Check dependencies
pip install -r requirements.txt
```

### Can't access admin commands?
```bash
# Verify your user ID
cat .env | grep BOT_OWNER_ID

# Get your ID from @userinfobot
# Update .env file
# Restart bot
```

### Import errors?
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### Games not working?
```bash
# Check if games loaded
python3 -c "from features.games import registry; print(len(registry.game_registry))"

# Should print: 23
```

---

## Production Deployment

### Using Screen (Simple)
```bash
# Start screen session
screen -S casino_bot

# Run bot
python main.py

# Detach: Ctrl+A then D
# Reattach: screen -r casino_bot
```

### Using Systemd (Recommended)
```bash
# Create service file
sudo nano /etc/systemd/system/casino-bot.service
```

```ini
[Unit]
Description=Telegram Casino Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Telegram-casino-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable casino-bot
sudo systemctl start casino-bot

# Check status
sudo systemctl status casino-bot

# View logs
sudo journalctl -u casino-bot -f
```

### Using Docker (Advanced)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

```bash
# Build
docker build -t casino-bot .

# Run
docker run -d --name casino-bot \
  --env-file .env \
  --restart unless-stopped \
  casino-bot
```

---

## Monitoring

### View Logs
```bash
# If using screen
screen -r casino_bot

# If using systemd
sudo journalctl -u casino-bot -f

# If using Docker
docker logs -f casino-bot
```

### Admin Dashboard
- Open your bot
- Send `/admin`
- View real-time statistics

### Performance
```bash
# Check memory usage
ps aux | grep main.py

# Check disk usage
du -sh /path/to/Telegram-casino-bot

# Check database size
du -sh data/
```

---

## Updating

### Pull Latest Changes
```bash
cd Telegram-casino-bot
git pull origin main
pip install -r requirements.txt
```

### Restart Bot
```bash
# If using screen
screen -r casino_bot
# Ctrl+C to stop, then python main.py

# If using systemd
sudo systemctl restart casino-bot

# If using Docker
docker restart casino-bot
```

---

## Backup

### Manual Backup
```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup configuration
cp .env .env.backup
```

### Automated Backup (cron)
```bash
# Edit crontab
crontab -e

# Add daily backup at 3 AM
0 3 * * * cd /path/to/bot && tar -czf backup-$(date +\%Y\%m\%d).tar.gz data/
```

---

## Security

### Best Practices
1. **Never commit .env file**
   - Already in .gitignore
   - Contains sensitive tokens

2. **Keep bot token secret**
   - Don't share publicly
   - Regenerate if compromised

3. **Backup private keys**
   - Blockchain wallet keys
   - Store securely offline

4. **Regular updates**
   - Update dependencies
   - Security patches

5. **Monitor logs**
   - Watch for errors
   - Check for suspicious activity

---

## Support & Resources

### Documentation
- `README.md` - Full setup guide
- `PROJECT_COMPLETE.md` - Complete project overview
- `GAMES_REFERENCE.md` - Game documentation
- `DEPLOYMENT_GUIDE.md` - Production deployment

### Code Structure
- `core/` - Core systems
- `features/` - All features
- `handlers/` - Command handlers
- `wallet/` - Blockchain integration

### Getting Help
1. Check documentation first
2. Review error logs
3. Search issues on GitHub
4. Contact project maintainer

---

## Success Checklist

- [ ] Python 3.9+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created and configured
- [ ] BOT_TOKEN set correctly
- [ ] BOT_OWNER_ID set correctly
- [ ] Bot starts without errors
- [ ] `/start` command works
- [ ] `/admin` command accessible
- [ ] Games are playable
- [ ] Demo balance works

**All checked? You're ready to go!** 🎉

---

## Quick Command Reference

### Essential
```bash
python main.py          # Start bot
pip install -r requirements.txt  # Install deps
cp .env.example .env    # Create config
```

### Testing
```bash
python -c "from features.games import registry; print(len(registry.game_registry))"  # Test games
python -c "import config; print(config.BOT_TOKEN[:10])"  # Test config
```

### Production
```bash
screen -S bot && python main.py  # Run in screen
sudo systemctl start casino-bot  # Run with systemd
docker-compose up -d             # Run with Docker
```

---

**That's it! Your bot is ready to launch!** 🚀

For detailed information, see the full documentation in the repository.
