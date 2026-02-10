#!/usr/bin/env python3
"""
TimeTree to Discord Notification Script

Fetches events from TimeTree and sends notifications to Discord via webhook.
- Today's events
- Tomorrow's events

Usage:
    python main.py
    python main.py --list  # List available calendars
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

from timetree_scraper import (
    TimeTreeScraper,
    LoginError,
    CalendarNotFoundError,
    TimeTreeScraperError
)
from discord_notifier import DiscordNotifier, DiscordNotifierError


def load_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()

    config = {
        "timetree_email": os.getenv("TIMETREE_EMAIL"),
        "timetree_password": os.getenv("TIMETREE_PASSWORD"),
        "timetree_calendar_id": os.getenv("TIMETREE_CALENDAR_ID"),
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL"),
    }

    # Validate required fields
    missing = []
    if not config["timetree_email"]:
        missing.append("TIMETREE_EMAIL")
    if not config["timetree_password"]:
        missing.append("TIMETREE_PASSWORD")
    if not config["discord_webhook_url"]:
        missing.append("DISCORD_WEBHOOK_URL")

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Please set them in .env file (see .env.example for reference)")
        sys.exit(1)

    return config


def list_calendars(scraper):
    """List all available calendars."""
    print("\n=== Available Calendars ===")
    calendars = scraper.get_calendars()
    for i, cal in enumerate(calendars, 1):
        print(f"{i}. {cal['name']} (ID: {cal['id']})")
    print("==========================\n")
    return calendars


def get_events_for_date(scraper, calendar_id, target_date):
    """Get events for a specific date."""
    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    all_events = scraper.get_events(calendar_id)

    filtered = []
    for event in all_events:
        event_start = event.get("start")
        if event_start:
            if start <= event_start < end:
                filtered.append(event)
            # Include all-day events that span this day
            elif event.get("all_day") and event_start <= end:
                event_end = event.get("end")
                if event_end and event_end > start:
                    filtered.append(event)

    return filtered


def main():
    """Main entry point."""
    now = datetime.now()
    print(f"Starting TimeTree to Discord notification... [{now.strftime('%Y-%m-%d %H:%M:%S')}]")

    # Check for list calendars option
    if len(sys.argv) > 1 and sys.argv[1] in ["--list", "-l"]:
        config = load_config()
        scraper = TimeTreeScraper(
            email=config["timetree_email"],
            password=config["timetree_password"]
        )
        scraper.login()
        list_calendars(scraper)
        return

    # Load configuration
    config = load_config()

    # Initialize scraper
    scraper = TimeTreeScraper(
        email=config["timetree_email"],
        password=config["timetree_password"]
    )

    try:
        # Login to TimeTree
        print("Logging in to TimeTree...")
        scraper.login()
        print("Login successful")

        # Get calendars if no specific calendar ID
        if not config["timetree_calendar_id"]:
            print("Fetching calendars...")
            calendars = scraper.get_calendars()
            if calendars:
                config["timetree_calendar_id"] = calendars[0]["id"]
                print(f"Using calendar: {calendars[0]['name']} (ID: {calendars[0]['id']})")
            else:
                print("Error: No calendars found")
                sys.exit(1)
        else:
            print(f"Using configured calendar ID: {config['timetree_calendar_id']}")

        # Get today's events
        print(f"Fetching today's events...")
        today_events = get_events_for_date(
            scraper,
            config["timetree_calendar_id"],
            now
        )

        # Get tomorrow's events
        tomorrow = now + timedelta(days=1)
        print(f"Fetching tomorrow's events...")
        tomorrow_events = get_events_for_date(
            scraper,
            config["timetree_calendar_id"],
            tomorrow
        )

        print(f"Found {len(today_events)} today's event(s), {len(tomorrow_events)} tomorrow's event(s)")

        # Send to Discord
        print("Sending to Discord...")
        notifier = DiscordNotifier(config["discord_webhook_url"])

        # Send daily notification (today + tomorrow)
        notifier.send_daily_notification(
            today_events=today_events,
            tomorrow_events=tomorrow_events,
            current_date=now,
            tomorrow_date=tomorrow
        )

        # On Monday, also send weekly notification
        if now.weekday() == 0:  # 0 = Monday
            print("Monday detected - sending weekly notification...")
            week_end = now + timedelta(days=6)  # Sunday
            week_events = scraper.get_upcoming_events(config["timetree_calendar_id"], days=7)

            # Create custom title for weekly notification
            week_title = f"📅 今週の予定 ({now.month}/{now.day} 〜 {week_end.month}/{week_end.day})"

            # Send weekly notification using existing send_events with custom title
            embeds = notifier._create_embeds(week_events)
            if embeds:
                embeds[0]["title"] = week_title

            payload = {"embeds": embeds} if embeds else {
                "embeds": [{
                    "title": week_title,
                    "description": "予定はありません 🎉",
                    "color": 0x57F287,
                    "footer": {"text": f"{now.strftime('%Y/%m/%d %H:%M')} 更新"}
                }]
            }

            requests.post(
                config["discord_webhook_url"],
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            print("Weekly notification sent")

        print("Notification sent successfully")

    except LoginError as e:
        print(f"Login failed: {e}")
        print("Please check your TIMETREE_EMAIL and TIMETREE_PASSWORD in .env")
        sys.exit(1)

    except CalendarNotFoundError as e:
        print(f"Calendar error: {e}")
        sys.exit(1)

    except TimeTreeScraperError as e:
        print(f"TimeTree scraper error: {e}")
        sys.exit(1)

    except DiscordNotifierError as e:
        print(f"Discord notification error: {e}")
        print("Please check your DISCORD_WEBHOOK_URL in .env")
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("Done!")


if __name__ == "__main__":
    main()
