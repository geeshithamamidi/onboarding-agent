"""
Mock MCP Tool Servers for the Smart Employee Onboarding Orchestrator.

Each tool simulates a real enterprise system (HRIS, GitHub, Slack, etc.)
with realistic fake responses. In production, these would be replaced by
real MCP server endpoints via stdio or SSE transport.

This demonstrates the MCP pattern: the orchestrator calls tools through
a standard interface — swapping mock for real requires zero changes to
the agent logic, only the tool registration.
"""

from .hris import HRISTools
from .it_provisioning import ITProvisioningTools
from .slack import SlackTools
from .github import GitHubTools
from .calendar import CalendarTools
from .email import EmailTools

__all__ = [
    "HRISTools",
    "ITProvisioningTools",
    "SlackTools",
    "GitHubTools",
    "CalendarTools",
    "EmailTools",
]
