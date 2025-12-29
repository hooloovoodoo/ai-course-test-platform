#!/usr/bin/env python3
"""
Email Notifier for AI Quiz System

Sends personalized bilingual email notifications with quiz URLs to recipients.
Reads English and Serbian quiz URLs from separate files and sends each recipient
one random URL from each language.
"""

import argparse
import logging
import os
import random
import smtplib
from smtplib import SMTPException, SMTPServerDisconnected, SMTPAuthenticationError
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles sending bilingual quiz notification emails."""

    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")

        if not self.sender_email or not self.sender_password:
            raise ValueError(
                "SENDER_EMAIL and SENDER_PASSWORD environment variables must be set"
            )

    def read_urls_from_file(self, file_path: str) -> List[str]:
        """Read URLs from a text file, one URL per line."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
            logger.info("Read %d URLs from %s", len(urls), file_path)
            return urls
        except FileNotFoundError:
            logger.error("File not found: %s", file_path)
            return []
        except RuntimeError as e:
            logger.error("Error reading URLs from %s: %s", file_path, e)
            return []

    def read_recipients_from_file(self, file_path: str) -> List[str]:
        """Read email addresses from a text file, one email per line."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                emails = [line.strip() for line in f if line.strip() and "@" in line]
            logger.info("Read %d email addresses from %s", len(emails), file_path)
            return emails
        except FileNotFoundError:
            logger.error("File not found: %s", file_path)
            return []
        except RuntimeError as e:
            logger.error("Error reading recipients from %s: %s", file_path, e)
            return []

    def create_html_email_content(self, en_url: str, sr_url: str) -> str:
        """Create HTML email content with bilingual quiz links."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .quiz-section {{
                    margin: 20px 0;
                    padding: 15px;
                    background-color: white;
                    border-radius: 5px;
                    border-left: 4px solid #4CAF50;
                }}
                .quiz-button {{
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white !important;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .quiz-button:hover {{
                    background-color: #45a049;
                    color: white !important;
                }}
                .quiz-button:visited {{
                    color: white !important;
                }}
                .quiz-button:link {{
                    color: white !important;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧠 AI Citizen Test</h1>
            </div>

            <p><strong>Instructions / Uputstva:</strong></p>
            <ul>
                <li>Choose one test in your preferred language
                    / Izaberite test na željenom jeziku</li>
                <li>Complete all questions to receive your score
                    / Odgovorite na sva pitanja da biste dobili rezultat</li>
                <li>Each test takes approximately 15-20 minutes
                    / Svaki test traje približno 15-20 minuta</li>
                <li>Email with results (PASS/FAIL) will be sent to you after you complete the test
                    / Posle završetka testa, dobićete email sa vašim rezultatom (PASS/FAIL)</li>
            </ul>

            <div class="content">
                <div class="quiz-section">
                    <h3>🇺🇸 / 🇬🇧 English Test</h3>
                    <p>Test your knowledge of AI Citizen with our comprehensive test. Good luck!</p>
                    <a href="{en_url}" class="quiz-button">Take English Test</a>
                </div>

                <div class="quiz-section">
                    <h3>🇷🇸 Srpski Test</h3>
                    <p>Testirajte svoje znanje o osnovama veštačke inteligencije. Srećno!</p>
                    <a href="{sr_url}" class="quiz-button">Započni Srpski Test</a>
                </div>
            </div>

            <div class="footer">
                <p><em>This is an automated message. Please do not reply to this email.</em><br>
                <em>Ovo je automatska poruka. Molimo ne odgovarajte na ovaj email.</em><br>
                <em>HLV 💚 YOU \\o/ :)</em></p>
            </div>

        </body>
        </html>
        """
        return html_content

    def create_plain_text_content(self, en_url: str, sr_url: str) -> str:
        """Create plain text email content as fallback."""
        text_content = f"""
AI Citizen Test
===============

Hello! You have been invited to take the AI Citizen test.

ENGLISH TEST:
{en_url}

SERBIAN TEST / SRPSKI TEST:
{sr_url}

Instructions / Uputstva:
- Choose one test in your preferred language / Izaberite test na željenom jeziku
- Complete all questions to receive your score / Odgovorite na sva pitanja da biste dobili rezultat
- Each test takes approximately 15-20 minutes / Svaki test traje približno 15-20 minuta
- Email with your results (PASS/FAIL) will be sent to you after you complete the test / Posle završetka testa, dobićete email sa vašim rezultatom (PASS/FAIL)

This is an automated message. Please do not reply to this email.
Ovo je automatska poruka. Molimo ne odgovarajte na ovaj email.
HLV 💚 YOU \\o/ :)
        """
        return text_content.strip()

    def send_email(self, recipient: str, en_url: str, sr_url: str) -> bool:
        """Send a bilingual quiz email to a single recipient."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.sender_email
            msg["To"] = recipient
            msg["Subject"] = "🧠 AI Citizen Test"

            # Create both HTML and plain text versions
            text_content = self.create_plain_text_content(en_url, sr_url)
            html_content = self.create_html_email_content(en_url, sr_url)

            # Attach parts
            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")

            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info("Email sent successfully to %s", recipient)
            return True

        except SMTPServerDisconnected as e:
            logger.error(
                "SMTP server disconnected while sending to %s: %s. This may be due to rate limiting or connection issues.",
                recipient,
                e,
            )
            return False
        except SMTPAuthenticationError as e:
            logger.error(
                "SMTP authentication failed while sending to %s: %s", recipient, e
            )
            return False
        except SMTPException as e:
            logger.error("SMTP error while sending to %s: %s", recipient, e)
            return False
        except Exception as e:
            logger.error("Unexpected error while sending to %s: %s", recipient, e)
            return False

    def send_batch_emails(
        self, en_urls_file: str, sr_urls_file: str, recipients_file: str
    ) -> dict:
        """Send emails to all recipients with random quiz URLs."""
        # Read all files
        en_urls = self.read_urls_from_file(en_urls_file)
        sr_urls = self.read_urls_from_file(sr_urls_file)
        recipients = self.read_recipients_from_file(recipients_file)

        if not en_urls:
            logger.error("No English URLs found")
            return {"success": 0, "failed": 0, "errors": ["No English URLs found"]}

        if not sr_urls:
            logger.error("No Serbian URLs found")
            return {"success": 0, "failed": 0, "errors": ["No Serbian URLs found"]}

        if not recipients:
            logger.error("No recipients found")
            return {"success": 0, "failed": 0, "errors": ["No recipients found"]}

        logger.info("Sending emails to %d recipients", len(recipients))
        logger.info(
            "Available: %d English URLs, %d Serbian URLs", len(en_urls), len(sr_urls)
        )

        results = {"success": 0, "failed": 0, "errors": []}
        consecutive_failures = 0

        for i, recipient in enumerate(recipients):
            # Select random URLs for this recipient
            en_url = random.choice(en_urls)
            sr_url = random.choice(sr_urls)

            logger.info(
                "Sending to %s - EN: %s... SR: %s...",
                recipient,
                en_url[:50],
                sr_url[:50],
            )

            if self.send_email(recipient, en_url, sr_url):
                results["success"] += 1
                consecutive_failures = 0
            else:
                results["failed"] += 1
                consecutive_failures += 1
                results["errors"].append(f"Failed to send to {recipient}")

                # If we have multiple consecutive failures, it might be rate limiting
                if consecutive_failures >= 3:
                    logger.warning(
                        "Multiple consecutive failures detected (%d). This may indicate rate limiting. "
                        "Consider adding longer delays between emails or splitting the batch.",
                        consecutive_failures,
                    )

            # Add a small delay between emails to avoid rate limiting
            # Skip delay after the last email
            if i < len(recipients) - 1:
                time.sleep(1)  # 1 second delay between emails

        return results


def main():
    """Main function to handle command line execution."""
    parser = argparse.ArgumentParser(
        description="Send bilingual quiz notification emails"
    )
    parser.add_argument(
        "en_urls_file", help="File with English quiz URLs (one per line)"
    )
    parser.add_argument(
        "sr_urls_file", help="File with Serbian quiz URLs (one per line)"
    )
    parser.add_argument(
        "recipients_file", help="File with recipient emails (one per line)"
    )
    parser.add_argument("--smtp-server", default="smtp.gmail.com", help="SMTP server")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP port")

    args = parser.parse_args()

    # Validate input files exist
    for file_path in [args.en_urls_file, args.sr_urls_file, args.recipients_file]:
        if not Path(file_path).exists():
            logger.error("File not found: %s", file_path)
            sys.exit(1)

    try:
        # Create notifier and send emails
        notifier = EmailNotifier(args.smtp_server, args.smtp_port)
        results = notifier.send_batch_emails(
            args.en_urls_file, args.sr_urls_file, args.recipients_file
        )

        # Report results
        logger.info("Email sending completed:")
        logger.info("  Success: %d", results["success"])
        logger.info("  Failed: %d", results["failed"])

        if results["errors"]:
            logger.error("Errors encountered:")
            for error in results["errors"]:
                logger.error("  - %s", error)

        if results["failed"] > 0:
            sys.exit(1)

    except RuntimeError as e:
        logger.error("Email notifier failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
