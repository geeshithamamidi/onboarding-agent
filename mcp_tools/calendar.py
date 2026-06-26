"""Mock Google Calendar MCP Tool Server."""

from datetime import datetime, timedelta
from typing import Any

_CALENDAR_EVENTS: list[dict] = []
_EVENT_COUNTER = 0


class CalendarTools:

    TOOL_SCHEMAS = [
        {
            "name": "calendar_schedule_session",
            "description": "Schedule a calendar event/meeting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM (24h)"},
                    "duration_mins": {"type": "integer"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "recurring": {"type": "boolean", "default": False},
                    "recurrence_rule": {"type": "string", "description": "RRULE string e.g. FREQ=WEEKLY;COUNT=12"}
                },
                "required": ["title", "date", "duration_mins", "attendees"]
            }
        }
    ]

    @staticmethod
    def calendar_schedule_session(
        title: str,
        date: str,
        duration_mins: int,
        attendees: list[str],
        time: str = "09:00",
        description: str = "",
        recurring: bool = False,
        recurrence_rule: str = "",
    ) -> dict[str, Any]:
        global _EVENT_COUNTER
        _EVENT_COUNTER += 1
        event_id = f"evt-{_EVENT_COUNTER:04d}"

        event = {
            "event_id": event_id,
            "title": title,
            "date": date,
            "time": time,
            "duration_mins": duration_mins,
            "attendees": attendees,
            "description": description,
            "recurring": recurring,
            "recurrence_rule": recurrence_rule,
            "calendar_link": f"https://calendar.google.com/event?id={event_id}",
            "created_at": datetime.now().isoformat()
        }
        _CALENDAR_EVENTS.append(event)

        return {
            "success": True,
            "event_id": event_id,
            "title": title,
            "date": date,
            "time": time,
            "duration_mins": duration_mins,
            "attendees_count": len(attendees),
            "calendar_link": event["calendar_link"],
            "message": f"Event '{title}' scheduled for {date} at {time}."
        }

    @staticmethod
    def get_all_events() -> list[dict]:
        return _CALENDAR_EVENTS

    def dispatch(self, tool_name: str, params: dict) -> dict[str, Any]:
        if tool_name == "calendar_schedule_session":
            return self.calendar_schedule_session(**params)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
