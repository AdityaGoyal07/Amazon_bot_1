"""
notifier.py — Multi-channel Notification Bot
Supports Email (SMTP), Telegram Bot API, and WhatsApp (Twilio).
Triggers only on meaningful changes: new best phone or price drop.
"""

import json
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Previous-state store (simple JSON file) ────────────────────────────────────
STATE_FILE = Path("data/last_best.json")


def _load_last_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(rec: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(rec, indent=2, ensure_ascii=False))


# ── Change detection ───────────────────────────────────────────────────────────

def should_notify(new_rec: dict, price_drop_threshold: float = 0.02) -> tuple[bool, str]:
    """
    Returns (should_send, reason_string).
    Triggers if:
      - Different best phone than last run
      - Price dropped by > threshold (default 2%)
    """
    last = _load_last_state()
    if not last:
        return True, "🆕 First run — best phone found!"

    last_name  = last.get("best_phone", "")
    last_price = last.get("price", 0)
    new_name   = new_rec.get("best_phone", "")
    new_price  = new_rec.get("price", 0)

    if new_name != last_name:
        return True, f"📱 New best phone: **{new_name}** (was: {last_name})"

    if last_price and new_price:
        drop = (last_price - new_price) / last_price
        if drop >= price_drop_threshold:
            pct = drop * 100
            return True, f"💰 Price drop of {pct:.1f}%: ₹{last_price:,} → ₹{new_price:,}"

    return False, ""


# ── Message builder ────────────────────────────────────────────────────────────

def _build_message(rec: dict, reason: str, budget: int) -> tuple[str, str]:
    """Returns (subject, body) for use across channels."""
    alts = rec.get("alternatives", [])
    alt_lines = "\n".join(
        f"  {i+1}. {a['name']} — ₹{a['price']:,}\n     {a['reason']}"
        for i, a in enumerate(alts)
    )
    subject = f"Amazon India Deal Alert: {rec.get('best_phone', 'N/A')}"
    body = f"""
🤖 Amazon India Smartphone Bot — Deal Alert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Budget: ₹{budget:,}
Trigger: {reason}

🏆 BEST PHONE
  {rec.get('best_phone')}  →  ₹{rec.get('price', 0):,}
  {rec.get('reason')}

🥈 ALTERNATIVES
{alt_lines}

View on Amazon: {rec.get('url', 'See results JSON')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
    return subject, body


# ── Email (SMTP) ───────────────────────────────────────────────────────────────

def send_email(
    rec: dict,
    reason: str,
    budget: int,
    smtp_host: str,
    smtp_port: int,
    sender: str,
    password: str,
    recipients: list[str],
    use_tls: bool = True,
) -> bool:
    """
    Send deal alert via SMTP email.

    Gmail example:
      smtp_host = "smtp.gmail.com"
      smtp_port = 587
      sender    = "your@gmail.com"
      password  = "<App Password>"   # NOT your Google password
    """
    subject, body = _build_message(rec, reason, budget)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        if use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(sender, password)
                server.sendmail(sender, recipients, msg.as_string())
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                server.login(sender, password)
                server.sendmail(sender, recipients, msg.as_string())
        logger.info(f"📧 Email sent to {recipients}")
        return True
    except Exception as exc:
        logger.error(f"Email failed: {exc}")
        return False


# ── Telegram ───────────────────────────────────────────────────────────────────

def send_telegram(
    rec: dict,
    reason: str,
    budget: int,
    bot_token: str,
    chat_id: str,
) -> bool:
    """
    Send via Telegram Bot API.

    Setup:
      1. Message @BotFather on Telegram → /newbot → copy token
      2. Message your bot once, then visit:
         https://api.telegram.org/bot<TOKEN>/getUpdates
         to find your chat_id
    """
    import urllib.request, urllib.parse

    _, body = _build_message(rec, reason, budget)
    # Telegram uses Markdown
    text = body.replace("━", "─")

    url     = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "Markdown",
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info(f"✈️  Telegram message sent to chat {chat_id}")
                return True
    except Exception as exc:
        logger.error(f"Telegram failed: {exc}")
    return False


# ── WhatsApp (Twilio) ──────────────────────────────────────────────────────────

def send_whatsapp(
    rec: dict,
    reason: str,
    budget: int,
    account_sid: str,
    auth_token: str,
    from_number: str,       # e.g. "whatsapp:+14155238886"
    to_number: str,         # e.g. "whatsapp:+919876543210"
) -> bool:
    """
    Send via Twilio WhatsApp API.

    Setup:
      1. Sign up at https://www.twilio.com
      2. Enable WhatsApp Sandbox in Twilio Console
      3. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN env vars
    """
    try:
        from twilio.rest import Client
    except ImportError:
        logger.error("twilio not installed. Run: pip install twilio")
        return False

    _, body = _build_message(rec, reason, budget)
    try:
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=from_number,
            to=to_number,
            body=body[:1600],   # WhatsApp char limit
        )
        logger.info(f"💬 WhatsApp sent. SID: {msg.sid}")
        return True
    except Exception as exc:
        logger.error(f"WhatsApp failed: {exc}")
        return False


# ── Unified notify function ────────────────────────────────────────────────────

def notify(
    rec: dict,
    budget: int,
    config: dict,
    force: bool = False,
) -> None:
    """
    Checks if notification should be sent, then dispatches to
    configured channels (email / telegram / whatsapp).

    Args:
        rec:    Recommendation dict from recommender.get_recommendation()
        budget: User's budget
        config: Notification config dict (see config.yaml for schema)
        force:  Send even if no change detected
    """
    should_send, reason = should_notify(rec)

    if not should_send and not force:
        logger.info("🔕 No change detected — skipping notification.")
        return

    logger.info(f"🔔 Sending notification — {reason}")
    nc = config.get("notifications", {})

    # ── Email ──────────────────────────────────────────────────────────────────
    if nc.get("email", {}).get("enabled"):
        ec = nc["email"]
        send_email(
            rec, reason, budget,
            smtp_host  = ec.get("smtp_host", "smtp.gmail.com"),
            smtp_port  = ec.get("smtp_port", 587),
            sender     = ec.get("sender")   or os.getenv("EMAIL_SENDER", ""),
            password   = ec.get("password") or os.getenv("EMAIL_PASSWORD", ""),
            recipients = ec.get("recipients", []),
        )

    # ── Telegram ───────────────────────────────────────────────────────────────
    if nc.get("telegram", {}).get("enabled"):
        tc = nc["telegram"]
        send_telegram(
            rec, reason, budget,
            bot_token = tc.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id   = tc.get("chat_id")   or os.getenv("TELEGRAM_CHAT_ID", ""),
        )

    # ── WhatsApp ───────────────────────────────────────────────────────────────
    if nc.get("whatsapp", {}).get("enabled"):
        wc = nc["whatsapp"]
        send_whatsapp(
            rec, reason, budget,
            account_sid = wc.get("account_sid") or os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token  = wc.get("auth_token")  or os.getenv("TWILIO_AUTH_TOKEN", ""),
            from_number = wc.get("from_number", ""),
            to_number   = wc.get("to_number", ""),
        )

    # Save state after successful notify
    _save_state(rec)
