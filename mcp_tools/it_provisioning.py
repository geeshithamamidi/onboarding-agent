"""
Mock IT Provisioning MCP Tool Server.

Simulates provisioning across email, GitHub, Slack, and license management.
"""

import random
import string
from typing import Any


_PROVISIONED: dict[str, dict] = {}


class ITProvisioningTools:

    TOOL_SCHEMAS = [
        {
            "name": "it_create_email",
            "description": "Create a corporate email account for the employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "corporate_email": {"type": "string"}
                },
                "required": ["employee_id", "corporate_email"]
            }
        },
        {
            "name": "it_provision_github",
            "description": "Add employee to GitHub organization teams.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "teams": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["employee_id", "teams"]
            }
        },
        {
            "name": "it_provision_slack",
            "description": "Create Slack account and add to channels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "corporate_email": {"type": "string"},
                    "channels": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["employee_id", "corporate_email", "channels"]
            }
        },
        {
            "name": "it_assign_licenses",
            "description": "Assign software licenses to employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "license_list": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["employee_id", "license_list"]
            }
        },
    ]

    @staticmethod
    def it_create_email(employee_id: str, corporate_email: str) -> dict[str, Any]:
        if corporate_email in [v.get("email") for v in _PROVISIONED.values()]:
            return {
                "success": False,
                "error": "EMAIL_CONFLICT",
                "message": f"{corporate_email} is already taken."
            }
        _PROVISIONED.setdefault(employee_id, {})["email"] = corporate_email
        return {
            "success": True,
            "corporate_email": corporate_email,
            "mailbox_size_gb": 50,
            "aliases": [f"alias-{corporate_email}"],
            "message": f"Corporate email {corporate_email} created."
        }

    @staticmethod
    def it_provision_github(employee_id: str, teams: list[str]) -> dict[str, Any]:
        username_base = _PROVISIONED.get(employee_id, {}).get("email", "user").split("@")[0]
        github_username = username_base.replace(".", "-")
        _PROVISIONED.setdefault(employee_id, {})["github"] = github_username
        return {
            "success": True,
            "github_username": github_username,
            "org": "company-org",
            "teams_added": teams,
            "role": "member",
            "message": f"GitHub account {github_username} created and added to {len(teams)} team(s)."
        }

    @staticmethod
    def it_provision_slack(employee_id: str, corporate_email: str, channels: list[str]) -> dict[str, Any]:
        slack_id = "U" + "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
        _PROVISIONED.setdefault(employee_id, {})["slack_id"] = slack_id
        return {
            "success": True,
            "slack_id": slack_id,
            "workspace": "company-workspace",
            "channels_joined": channels,
            "message": f"Slack account created. ID: {slack_id}. Joined {len(channels)} channel(s)."
        }

    @staticmethod
    def it_assign_licenses(employee_id: str, license_list: list[str]) -> dict[str, Any]:
        assigned = []
        failed = []
        for lic in license_list:
            # Simulate 95% success rate
            if random.random() > 0.05:
                assigned.append(lic)
            else:
                failed.append({"license": lic, "reason": "No seats available"})
        return {
            "success": len(failed) == 0,
            "licenses_assigned": assigned,
            "licenses_failed": failed,
            "message": f"Assigned {len(assigned)}/{len(license_list)} licenses."
        }

    def dispatch(self, tool_name: str, params: dict) -> dict[str, Any]:
        handlers = {
            "it_create_email": lambda p: self.it_create_email(**p),
            "it_provision_github": lambda p: self.it_provision_github(**p),
            "it_provision_slack": lambda p: self.it_provision_slack(**p),
            "it_assign_licenses": lambda p: self.it_assign_licenses(**p),
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return handler(params)
