"""Mock GitHub MCP Tool Server (used indirectly via IT provisioning)."""

from typing import Any

_GITHUB_ORG_MEMBERS: dict[str, list[str]] = {}


class GitHubTools:

    TOOL_SCHEMAS = [
        {
            "name": "github_add_to_team",
            "description": "Add a user to a GitHub organization team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "team_slug": {"type": "string"},
                    "role": {"type": "string", "enum": ["member", "maintainer"], "default": "member"}
                },
                "required": ["username", "team_slug"]
            }
        }
    ]

    @staticmethod
    def github_add_to_team(username: str, team_slug: str, role: str = "member") -> dict[str, Any]:
        _GITHUB_ORG_MEMBERS.setdefault(team_slug, []).append(username)
        return {
            "success": True,
            "username": username,
            "team": team_slug,
            "role": role,
            "org": "company-org",
            "url": f"https://github.com/orgs/company-org/teams/{team_slug}"
        }

    def dispatch(self, tool_name: str, params: dict) -> dict[str, Any]:
        if tool_name == "github_add_to_team":
            return self.github_add_to_team(**params)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
