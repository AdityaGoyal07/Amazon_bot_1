# 🤖 Amazon India Smartphone Bot

A fully automated, production-ready Python bot that:
- **Scrapes** Amazon India for smartphones within your budget
- **Filters & ranks** phones by a composite score (rating, reviews, brand, value)
- **Recommends** the best pick using OpenAI / Anthropic AI
- **Notifies** you via Email, Telegram, or WhatsApp
- **Schedules** daily runs via APScheduler

---

## 📁 Project Structure

```
amazon_bot/
├── main.py           # Entry point & CLI
├── scraper.py        # Playwright-based Amazon scraper (anti-bot)
├── processor.py      # Data cleaning, filtering & ranking engine
├── recommender.py    # AI recommendation layer (OpenAI / Anthropic)
├── notifier.py       # Email / Telegram / WhatsApp alerts
├── scheduler.py      # APScheduler daily job
├── config.yaml       # All settings (budget, keys, schedule)
├── requirements.txt  # Python dependencies
├── data/             # Auto-created: JSON/CSV outputs + state
└── logs/             # Auto-created: daily log files
```

---

## ⚙️ Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Playwright Chromium browser
```bash
playwright install chromium
```

### 3. Configure `config.yaml`
Edit the file to set:
- `scraper.budget` — your max price in INR (e.g. `30000`)
- `ai.openai_api_key` — your OpenAI key (or set `OPENAI_API_KEY` env var)
- Notification channels (email / telegram / whatsapp)

> **Security tip:** Never commit API keys. Use environment variables or a `.env` file with `python-dotenv`.

---

## 🚀 Running the Bot

### One-time run (uses config.yaml)
```bash
python main.py
```

### Override budget from CLI
```bash
python main.py --budget 20000
```

### Override budget + pages
```bash
python main.py --budget 15000 --pages 2
```

### Show browser window (debug)
Set `headless: false` in config.yaml, then:
```bash
python main.py --log-level DEBUG
```

### Dry run (use cached data, skip scraping)
```bash
python main.py --dry-run
```
> Place sample data in `data/dry_run.json` first.

### Run via scheduler (daily at configured time)
```bash
python main.py --schedule
```

### Run via system cron (alternative to APScheduler)
```bash
# Edit crontab:
crontab -e

# Add line to run at 9:00 AM IST daily:
0 9 * * * cd /path/to/amazon_bot && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

---

## 🔔 Notification Setup

### Email (Gmail)
1. Enable 2FA on your Google account
2. Generate an **App Password**: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Set in config.yaml or as env vars:
   ```bash
   export EMAIL_SENDER="your@gmail.com"
   export EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"
   ```

### Telegram
1. Message `@BotFather` on Telegram → `/newbot` → copy the token
2. Send any message to your new bot
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your `chat_id`
4. Set env vars:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
   export TELEGRAM_CHAT_ID="987654321"
   ```

### WhatsApp (Twilio)
1. Sign up at [twilio.com](https://www.twilio.com)
2. Enable WhatsApp Sandbox in console
3. Set env vars:
   ```bash
   export TWILIO_ACCOUNT_SID="AC..."
   export TWILIO_AUTH_TOKEN="..."
   ```

---

## 📊 Output

Each run produces:
- `data/phones_<budget>_<timestamp>.json` — all filtered + ranked phones
- `data/phones_<budget>_<timestamp>.csv`  — same data as CSV
- `data/recommendation_<budget>_<timestamp>.json` — AI recommendation
- `data/last_best.json` — state file for change detection
- `logs/bot_YYYYMMDD.log` — daily log file

### Example console output:
```
======================================================================
  🤖 Amazon India Smartphone Bot | Budget: ₹30,000
======================================================================

🏆 BEST PICK: Samsung Galaxy S23 FE 5G (8GB RAM, 256GB)
   Price  : ₹26,999
   Reason : Offers a flagship-grade Snapdragon 8 Gen 1 chipset...

🥈 ALTERNATIVES:
  1. OnePlus 12R 5G  —  ₹29,999
  2. Google Pixel 7a  —  ₹27,999

📋 TOP 5 PHONES (by score):
  #   Name                                               Price  Rating   Reviews
  ─────────────────────────────────────────────────────────────────────────────
  1   Samsung Galaxy S23 FE 5G (8GB RAM, 256GB)       ₹26,999    4.3    12,456
  ...
```

---

## 🛡️ Anti-Detection Features
- Random user-agent rotation (5 UA pool)
- Human-like typing delays (40–120ms per character)
- Gradual page scrolling to trigger lazy-load
- Randomised navigation delays (0.8–4.0s)
- Browser fingerprint masking (removes `navigator.webdriver`)
- Locale & timezone set to India
- Retry logic with exponential backoff

---

## ⚠️ Legal & Ethical Note
Web scraping Amazon may violate their Terms of Service.
Use this bot for personal, non-commercial research only.
Consider using the [Amazon Product Advertising API](https://affiliate-program.amazon.in/help/node/topic/G200473530) for production use.
