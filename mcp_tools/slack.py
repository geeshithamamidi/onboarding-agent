"""Mock Slack MCP Tool Server."""

from datetime import datetime
from typing import Any

_MESSAGES_LOG: list[dict] = []


class SlackTools:

    TOOL_SCHEMAS = [
        {
            "name": "slack_post_message",
            "description": "Post a message to a Slack channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel name e.g. #general"},
                    "message": {"type": "string"},
                    "sender_name": {"type": "string", "description": "Display name for the bot"}
                },
                "required": ["channel", "message"]
            }
        }
    ]

    @staticmethod
    def slack_post_message(channel: str, message: str, sender_name: str = "Onboarding Bot") -> dict[str, Any]:
        ts = datetime.now().isoformat()
        entry = {
            "channel": channel,
            "message": message,
            "sender": sender_name,
            "timestamp": ts,
            "message_id": f"msg-{len(_MESSAGES_LOG)+1:04d}"
        }
        _MESSAGES_LOG.append(entry)
        print(f"\n  [SLACK → {channel}]\n  {message}\n")
        return {
            "success": True,
            "message_id": entry["message_id"],
            "channel": channel,
            "timestamp": ts
        }

    @staticmethod
    def get_log() -> list[dict]:
        return _MESSAGES_LOG

    def dispatch(self, tool_name: str, params: dict) -> dict[str, Any]:
        if tool_name == "slack_post_message":
            return self.slack_post_message(**params)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
