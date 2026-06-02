from __future__ import annotations

from dataclasses import dataclass
import os
import smtplib
from email.message import EmailMessage

import requests


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    message: str


def should_notify(total_price: int, threshold: int | None) -> bool:
    return threshold is not None and threshold > 0 and total_price <= threshold


def send_discord_notification(total_price: int, summary: str, webhook_url: str | None = None) -> NotificationResult:
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return NotificationResult(False, "Discord Webhook URLが未設定です。")
    response = requests.post(url, json={"content": f"旅行費用が {total_price:,} 円になりました。\n{summary}"}, timeout=15)
    if 200 <= response.status_code < 300:
        return NotificationResult(True, "Discordへ通知しました。")
    return NotificationResult(False, f"Discord通知に失敗しました: HTTP {response.status_code}")


def send_email_notification(total_price: int, summary: str) -> NotificationResult:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")
    mail_to = os.getenv("MAIL_TO")
    if not all([host, user, password, mail_from, mail_to]):
        return NotificationResult(False, "メール通知のSMTP設定が未設定です。")

    message = EmailMessage()
    message["Subject"] = f"旅行費用チェック: {total_price:,}円"
    message["From"] = mail_from
    message["To"] = mail_to
    message.set_content(f"旅行費用が {total_price:,} 円になりました。\n\n{summary}")

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)
    return NotificationResult(True, "メール通知を送信しました。")
