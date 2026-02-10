"""
Discord Notifier - Sends formatted event notifications to Discord webhooks.
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional


class DiscordNotifierError(Exception):
    """Base exception for Discord notifier errors."""
    pass


class DiscordNotifier:
    """Sends formatted messages to Discord via webhook."""

    def __init__(self, webhook_url: str):
        """
        Initialize the notifier with a webhook URL.

        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url

    def _format_date(self, dt: datetime) -> str:
        """Format datetime for Japanese display."""
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        return f"{dt.month}月{dt.day}日 ({weekdays[dt.weekday()]})"

    def _format_time(self, dt: datetime) -> str:
        """Format time for display."""
        return dt.strftime("%H:%M")

    def _format_event(self, event: Dict) -> str:
        """Format a single event for display."""
        lines = []

        # Time or "All day"
        if event.get("all_day"):
            lines.append("• 終日 - " + event.get("title", "Untitled"))
        elif event.get("start") and event.get("end"):
            start = self._format_time(event["start"])
            end = self._format_time(event["end"])
            lines.append(f"• {start} - {end} " + event.get("title", "Untitled"))
        else:
            lines.append("• " + event.get("title", "Untitled"))

        # Location if present
        if event.get("location"):
            lines.append(f"  📍 {event['location']}")

        return "\n".join(lines)

    def _create_embeds(self, events: List[Dict]) -> List[Dict]:
        """
        Create Discord embed objects from events.

        Args:
            events: List of event dictionaries

        Returns:
            List of Discord embed objects
        """
        if not events:
            return []

        embeds = []
        current_embed = {
            "title": "📅 今週のTimeTree予定",
            "color": 0x5865F2,  # Discord blurple color
            "fields": [],
            "footer": {"text": f"{datetime.now().strftime('%Y/%m/%d %H:%M')} 更新"}
        }

        # Group events by date
        events_by_date: Dict[str, List[Dict]] = {}
        for event in sorted(events, key=lambda e: e.get("start") or datetime.min):
            if event.get("start"):
                date_key = event["start"].date()
            else:
                date_key = datetime.now().date()

            if date_key not in events_by_date:
                events_by_date[date_key] = []
            events_by_date[date_key].append(event)

        # Add fields for each date
        for date, day_events in sorted(events_by_date.items()):
            date_str = self._format_date(datetime.combine(date, datetime.min.time()))
            field_value = "\n".join(self._format_event(e) for e in day_events)

            # Discord field value limit is 1024 characters
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."

            current_embed["fields"].append({
                "name": f"🗓️ {date_str}",
                "value": field_value,
                "inline": False
            })

        embeds.append(current_embed)
        return embeds

    def _create_daily_embeds(self, today_events: List[Dict], tomorrow_events: List[Dict],
                            current_date: datetime, tomorrow_date: datetime) -> List[Dict]:
        """
        Create Discord embed objects for daily notification.

        Args:
            today_events: List of today's events
            tomorrow_events: List of tomorrow's events
            current_date: Current datetime
            tomorrow_date: Tomorrow's datetime

        Returns:
            List of Discord embed objects
        """
        embeds = []
        today_str = self._format_date(current_date)
        tomorrow_str = self._format_date(tomorrow_date)

        # Today's events embed
        if today_events:
            field_value = "\n".join(self._format_event(e) for e in today_events)
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."

            embeds.append({
                "title": f"📅 今日の予定 - {today_str}",
                "color": 0x5865F2,  # Discord blurple
                "fields": [{
                    "name": "予定",
                    "value": field_value,
                    "inline": False
                }],
                "footer": {"text": f"{current_date.strftime('%Y/%m/%d %H:%M')} 更新"}
            })
        else:
            embeds.append({
                "title": f"📅 今日の予定 - {today_str}",
                "description": "**予定はありません**",
                "color": 0x57F287,  # Discord green
                "footer": {"text": f"{current_date.strftime('%Y/%m/%d %H:%M')} 更新"}
            })

        # Tomorrow's events embed
        if tomorrow_events:
            field_value = "\n".join(self._format_event(e) for e in tomorrow_events)
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."

            embeds.append({
                "title": f"📅 明日の予定 - {tomorrow_str}",
                "color": 0x5865F2,  # Discord blurple
                "fields": [{
                    "name": "予定",
                    "value": field_value,
                    "inline": False
                }],
                "footer": {"text": f"{current_date.strftime('%Y/%m/%d %H:%M')} 更新"}
            })
        else:
            embeds.append({
                "title": f"📅 明日の予定 - {tomorrow_str}",
                "description": "**予定はありません**",
                "color": 0x57F287,  # Discord green
                "footer": {"text": f"{current_date.strftime('%Y/%m/%d %H:%M')} 更新"}
            })

        return embeds

    def send_daily_notification(self, today_events: List[Dict], tomorrow_events: List[Dict],
                               current_date: datetime, tomorrow_date: datetime) -> bool:
        """
        Send daily notification to Discord webhook.

        Args:
            today_events: List of today's events
            tomorrow_events: List of tomorrow's events
            current_date: Current datetime
            tomorrow_date: Tomorrow's datetime

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordNotifierError: If sending fails
        """
        payload = {"embeds": self._create_daily_embeds(today_events, tomorrow_events, current_date, tomorrow_date)}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True

        except requests.RequestException as e:
            raise DiscordNotifierError(f"Failed to send Discord message: {e}")

    def send_events(self, events: List[Dict]) -> bool:
        """
        Send events to Discord webhook.

        Args:
            events: List of event dictionaries

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordNotifierError: If sending fails
        """
        if not events:
            # Send a "no events" message
            embed = {
                "title": "📅 今週のTimeTree予定",
                "description": "予定はありません 🎉",
                "color": 0x57F287,  # Discord green
                "footer": {"text": f"{datetime.now().strftime('%Y/%m/%d %H:%M')} 更新"}
            }
            payload = {"embeds": [embed]}
        else:
            payload = {"embeds": self._create_embeds(events)}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True

        except requests.RequestException as e:
            raise DiscordNotifierError(f"Failed to send Discord message: {e}")

    def send_raw(self, content: str, username: Optional[str] = None) -> bool:
        """
        Send raw text content to Discord webhook.

        Args:
            content: Text content to send
            username: Optional override for webhook username

        Returns:
            True if successful, False otherwise

        Raises:
            DiscordNotifierError: If sending fails
        """
        payload = {"content": content}
        if username:
            payload["username"] = username

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True

        except requests.RequestException as e:
            raise DiscordNotifierError(f"Failed to send Discord message: {e}")
