"""Mock Email MCP Tool Server."""

from datetime import datetime
from typing import Any

_EMAIL_LOG: list[dict] = []


class EmailTools:

    TOOL_SCHEMAS = [
        {
            "name": "email_send_document",
            "description": "Send an email with document attachments or content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "documents": {"type": "array", "items": {"type": "string"}},
                    "deadline": {"type": "string", "description": "YYYY-MM-DD, deadline for action"}
                },
                "required": ["recipient", "subject"]
            }
        }
    ]

    @staticmethod
    def email_send_document(
        recipient: str,
        subject: str,
        body: str = "",
        documents: list[str] = None,
        deadline: str = "",
    ) -> dict[str, Any]:
        documents = documents or []
        entry = {
            "to": recipient,
            "subject": subject,
            "body": body[:200] + "..." if len(body) > 200 else body,
            "attachments": documents,
            "deadline": deadline,
            "sent_at": datetime.now().isoformat(),
            "message_id": f"email-{len(_EMAIL_LOG)+1:04d}"
        }
        _EMAIL_LOG.append(entry)
        print(f"\n  [EMAIL → {recipient}]\n  Subject: {subject}\n  Docs: {documents}\n")
        return {
            "success": True,
            "message_id": entry["message_id"],
            "recipient": recipient,
            "subject": subject,
            "documents_sent": documents,
            "sent_at": entry["sent_at"]
        }

    @staticmethod
    def get_log() -> list[dict]:
        return _EMAIL_LOG

    def dispatch(self, tool_name: str, params: dict) -> dict[str, Any]:
        if tool_name == "email_send_document":
            return self.email_send_document(**params)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
