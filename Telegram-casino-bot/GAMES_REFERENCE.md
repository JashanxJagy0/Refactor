# Game Reference - All Implemented Games

## 🎮 Available Games (12 Total)

### House Games (7)

| Game | Commands | Bet | Params | Multiplier | Type |
|------|----------|-----|--------|------------|------|
| **Mines** | `/mines`, `/m` | Amount | Num mines (1-24) | 1.01x-291x | Interactive |
| **Coin Flip** | `/flip`, `/coinflip` | Amount | - | 1.94x-∞ (streak) | Interactive |
| **Dice Roll** | `/dice`, `/d` | Amount | Prediction (1-6) | 5.82x | Instant |
| **Tower** | `/tower`, `/tw` | Amount | Difficulty | 1.1x-125x | Interactive |
| **Roulette** | `/roulette`, `/ru` | Amount | Bet type + value | 2x-35x | Instant |
| **Slots** | `/slots`, `/sl` | Amount | - | 5.82x-14.5x | Instant |
| **Keno** | `/keno`, `/k` | Amount | 1-8 numbers | 3.5x-2000x | Instant |

### Single Emoji Games (5)

| Game | Command | Bet | Emoji | Win Condition | Multiplier |
|------|---------|-----|-------|---------------|------------|
| **Darts** | `/edarts` | Amount | 🎯 | Hit board (3-6) | 1.15x |
| **Soccer** | `/esoccer` | Amount | ⚽ | Goal (3-5) | 1.53x |
| **Basketball** | `/ebasket` | Amount | 🏀 | Basket (4-5) | 2.25x |
| **Bowling** | `/ebowl` | Amount | 🎳 | Strike (6) | 5.00x |
| **Slot** | `/eslot` | Amount | 🎰 | Match (1,22,43,64) | 14.5x |

## 📖 Usage Examples

### Mines
```
/mines 1.50 5                    # $1.50 bet with 5 mines
/m 10.00 10                      # $10 bet with 10 mines
```
- Click tiles to reveal
- Cash out anytime after first safe pick
- More mines = higher multipliers but more risk

### Coin Flip
```
/flip 2.00                       # $2.00 bet
/coinflip 5.00                   # $5.00 bet
```
- Pick Heads or Tails
- 1.94x on first win
- Each consecutive win doubles multiplier (2x, 4x, 8x...)
- Cash out or continue

### Dice Roll
```
/dice 1.00 6                     # Bet $1.00 on rolling 6
/d 2.50 3                        # Bet $2.50 on rolling 3
```
- Predict dice value (1-6)
- Instant result
- 5.82x if correct

### Tower
```
/tower 1.50 easy                 # Easy mode (4 tiles per floor)
/tower 2.00 medium               # Medium mode (3 tiles)
/tower 5.00 hard                 # Hard mode (2 tiles)
/tw 1.00                         # Medium mode (default)
```
- Climb 9 floors
- Avoid snakes
- Cash out at any floor
- Higher difficulty = higher multipliers

### Roulette
```
/roulette 1.50 red               # Bet on red (2x)
/roulette 1.50 single 17         # Bet on number 17 (35x)
/roulette 2.00 even              # Bet on even numbers (2x)
/roulette 1.00 high              # Bet on 19-36 (2x)
```
Bet types: single, red, black, even, odd, low (1-18), high (19-36)

### Slots
```
/slots 1.00                      # Spin slot machine
/sl 2.50                         # Spin with $2.50
```
- Telegram slot emoji animation
- Various win combinations
- Up to 14.5x jackpot

### Keno
```
/keno 1.50 5 12 23 45            # Pick 4 numbers
/k 2.00 7 14 21 28 35 42 49 56   # Pick 8 numbers
```
- Pick 1-8 numbers from 1-80
- 10 numbers drawn
- More matches = higher payout

### Emoji Games
```
/edarts 1.00                     # Emoji darts
/esoccer 1.00                    # Emoji soccer
/ebasket 1.00                    # Emoji basketball
/ebowl 1.00                      # Emoji bowling
/eslot 1.00                      # Emoji slot
```
- Simple one-shot games
- Telegram emoji animation
- Fixed multipliers on win

## 🎯 Game Types

### Interactive Games (3)
- **Mines**: Click tiles, cash out anytime
- **Coin Flip**: Continue streak or cash out
- **Tower**: Climb floors, cash out anytime

### Instant Games (9)
- **Dice Roll**: Immediate result
- **Roulette**: Immediate spin result
- **Slots**: Animated result (~3 sec)
- **Keno**: Immediate draw
- **All Emoji Games**: Animated result (~3 sec)

## 💰 Multiplier Ranges

| Range | Games |
|-------|-------|
| 1.15x-2.25x | Single emoji games |
| 2x-5.82x | Dice Roll, Roulette (non-single) |
| 1.94x-∞ | Coin Flip (streak) |
| 1.01x-291x | Mines (depends on bombs) |
| 1.1x-125x | Tower (depends on difficulty) |
| 3.5x-2000x | Keno (depends on picks) |
| 5.82x-14.5x | Slots |

## 🎲 Provably Fair

All games use provably fair cryptography:
- Server seed (hidden until game end)
- Client seed (player can set)
- Nonce (incremented per bet)
- SHA256 hashing for result generation

Game results are deterministic and verifiable.

## 💡 Tips

1. **Start Small**: Test games with minimum bets first
2. **Understand Risk**: Higher multipliers = lower win chance
3. **Cashout Strategy**: For interactive games, decide cashout points in advance
4. **Diversify**: Try different games to find your favorites
5. **Provably Fair**: All results are cryptographically fair

## 🏆 Best Games For...

- **Quick Wins**: Dice Roll, Emoji games
- **Big Multipliers**: Tower (hard), Keno
- **Strategy**: Mines, Tower, Coin Flip
- **Classic Casino**: Roulette, Slots
- **Low Risk**: Emoji Darts (1.15x), Emoji Soccer (1.53x)
- **High Risk**: Tower Hard (125x), Keno (2000x)
