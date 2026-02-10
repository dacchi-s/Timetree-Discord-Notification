"""
TimeTree Scraper - Fetches events from TimeTree via internal API.

Uses TimeTree web app's internal API endpoints (same as timetree-exporter).
"""

import uuid
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class TimeTreeScraperError(Exception):
    """Base exception for TimeTree scraper errors."""
    pass


class LoginError(TimeTreeScraperError):
    """Raised when login fails."""
    pass


class CalendarNotFoundError(TimeTreeScraperError):
    """Raised when calendar is not found."""
    pass


class TimeTreeScraper:
    """Scraper for fetching TimeTree calendar events."""

    API_BASEURI = "https://timetreeapp.com/api/v1"
    API_USER_AGENT = "web/2.1.0/en"

    def __init__(self, email: str, password: str):
        """
        Initialize the scraper with credentials.

        Args:
            email: TimeTree account email
            password: TimeTree account password
        """
        self.email = email
        self.password = password
        self.session_id = None
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests."""
        return {
            "Content-Type": "application/json",
            "X-Timetreea": self.API_USER_AGENT,
        }

    def login(self) -> None:
        """
        Authenticate with TimeTree and establish session.

        Raises:
            LoginError: If authentication fails
        """
        url = f"{self.API_BASEURI}/auth/email/signin"
        payload = {
            "uid": self.email,
            "password": self.password,
            "uuid": str(uuid.uuid4()).replace("-", ""),
        }

        try:
            response = requests.put(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code != 200:
                raise LoginError(f"Authentication failed: HTTP {response.status_code} - {response.text}")

            # Get session ID from cookie
            self.session_id = response.cookies.get("_session_id")
            if not self.session_id:
                raise LoginError("Failed to get session cookie")

            # Set the session cookie for future requests
            self.session.cookies.set("_session_id", self.session_id)

        except requests.RequestException as e:
            raise LoginError(f"Login request failed: {e}")

    def get_calendars(self) -> List[Dict[str, str]]:
        """
        Get list of user's calendars.

        Returns:
            List of calendars with id and name

        Raises:
            TimeTreeScraperError: If fetching calendars fails
        """
        try:
            url = f"{self.API_BASEURI}/calendars?since=0"
            response = self.session.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code != 200:
                raise TimeTreeScraperError(f"Failed to fetch calendars: HTTP {response.status_code}")

            data = response.json()
            calendars = []

            for cal in data.get("calendars", []):
                calendars.append({
                    "id": str(cal.get("id")),
                    "name": cal.get("name"),
                })

            return calendars

        except requests.RequestException as e:
            raise TimeTreeScraperError(f"Failed to fetch calendars: {e}")
        except ValueError as e:
            raise TimeTreeScraperError(f"Invalid response: {e}")

    def get_events(self, calendar_id: str) -> List[Dict]:
        """
        Fetch all events for a calendar.

        Args:
            calendar_id: TimeTree calendar ID

        Returns:
            List of event dictionaries with keys:
            - id: event ID
            - title: event title
            - start: start datetime
            - end: end datetime
            - all_day: boolean for all-day events
            - location: location string (optional)
            - description: event description (optional)
            - color: event color code

        Raises:
            TimeTreeScraperError: If fetching events fails
        """
        try:
            url = f"{self.API_BASEURI}/calendar/{calendar_id}/events/sync"
            response = self.session.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code != 200:
                raise TimeTreeScraperError(f"Failed to fetch events: HTTP {response.status_code}")

            data = response.json()
            events = []

            for ev in data.get("events", []):
                event_data = {
                    "id": ev.get("id"),
                    "title": ev.get("title", "Untitled"),
                    "all_day": ev.get("all_day", False),
                    "location": ev.get("location"),
                    "description": ev.get("note"),
                    "color": ev.get("label_id"),
                }

                # Parse start/end times (milliseconds since epoch)
                if ev.get("start_at"):
                    try:
                        # TimeTree returns milliseconds since epoch
                        start_ms = ev["start_at"]
                        event_data["start"] = datetime.fromtimestamp(start_ms / 1000)
                    except (TypeError, ValueError):
                        event_data["start"] = None

                if ev.get("end_at"):
                    try:
                        end_ms = ev["end_at"]
                        event_data["end"] = datetime.fromtimestamp(end_ms / 1000)
                    except (TypeError, ValueError):
                        event_data["end"] = None

                events.append(event_data)

            # Handle chunked responses
            if data.get("chunk") is True:
                since = data.get("since")
                if since:
                    events.extend(self._get_events_recursive(calendar_id, since))

            return events

        except requests.RequestException as e:
            raise TimeTreeScraperError(f"Failed to fetch events: {e}")
        except ValueError as e:
            raise TimeTreeScraperError(f"Invalid response: {e}")

    def _get_events_recursive(self, calendar_id: str, since: int) -> List[Dict]:
        """Recursively fetch event chunks."""
        try:
            url = f"{self.API_BASEURI}/calendar/{calendar_id}/events/sync?since={since}"
            response = self.session.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code != 200:
                return []

            data = response.json()
            events = []

            for ev in data.get("events", []):
                event_data = {
                    "id": ev.get("id"),
                    "title": ev.get("title", "Untitled"),
                    "all_day": ev.get("all_day", False),
                    "location": ev.get("location"),
                    "description": ev.get("note"),
                    "color": ev.get("label_id"),
                }

                if ev.get("start_at"):
                    try:
                        start_ms = ev["start_at"]
                        event_data["start"] = datetime.fromtimestamp(start_ms / 1000)
                    except (TypeError, ValueError):
                        event_data["start"] = None

                if ev.get("end_at"):
                    try:
                        end_ms = ev["end_at"]
                        event_data["end"] = datetime.fromtimestamp(end_ms / 1000)
                    except (TypeError, ValueError):
                        event_data["end"] = None

                events.append(event_data)

            # Continue recursion if there are more chunks
            if data.get("chunk") is True:
                events.extend(self._get_events_recursive(calendar_id, data.get("since")))

            return events

        except (requests.RequestException, ValueError):
            return []

    def get_upcoming_events(
        self,
        calendar_id: Optional[str] = None,
        days: int = 7
    ) -> List[Dict]:
        """
        Get events for the next N days starting from today.

        Args:
            calendar_id: Specific calendar ID (auto-selects first if None)
            days: Number of days to fetch (default: 7)

        Returns:
            List of events in the date range
        """
        if not calendar_id:
            calendars = self.get_calendars()
            if not calendars:
                raise CalendarNotFoundError("No calendars found")
            calendar_id = calendars[0]["id"]

        # Get all events and filter by date range
        all_events = self.get_events(calendar_id)

        # Filter events for the next N days
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=days)

        filtered_events = []
        for event in all_events:
            event_start = event.get("start")
            if event_start:
                # Include events that start within the range
                if start_date <= event_start < end_date:
                    filtered_events.append(event)
                # Also include all-day events that might span multiple days
                elif event.get("all_day") and event_start <= end_date:
                    # Check if event ends after start_date
                    event_end = event.get("end")
                    if event_end and event_end > start_date:
                        filtered_events.append(event)

        return filtered_events
