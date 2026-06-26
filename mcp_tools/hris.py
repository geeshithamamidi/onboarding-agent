"""
Mock HRIS (Human Resources Information System) MCP Tool Server.

Simulates a real HRIS like Workday or BambooHR.
In production: replace with MCP server over stdio/SSE pointing at real API.
"""

import uuid
from datetime import datetime
from typing import Any


# Simulated in-memory database
_EMPLOYEE_DB: dict[str, dict] = {}

_VALID_DEPARTMENTS = [
    "Engineering", "Product", "Design", "Data & Analytics",
    "Marketing", "Sales", "Finance", "People Operations",
    "Legal", "Customer Success", "Operations"
]


class HRISTools:
    """Mock HRIS tool server — models MCP tool schema + handler pattern."""

    # MCP tool schema definitions (what the agent sees)
    TOOL_SCHEMAS = [
        {
            "name": "hris_create_employee",
            "description": "Create a new employee record in the HRIS system. Returns an employee_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "personal_email": {"type": "string"},
                    "role": {"type": "string"},
                    "department": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "employment_type": {"type": "string", "enum": ["full_time", "part_time", "contractor"]},
                    "manager_name": {"type": "string"},
                    "compensation": {"type": "number"},
                },
                "required": ["full_name", "personal_email", "role", "department", "start_date"]
            }
        },
        {
            "name": "hris_get_departments",
            "description": "Returns the list of valid department names in the organization.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        },
        {
            "name": "hris_get_employee",
            "description": "Retrieve an employee record by employee_id.",
            "parameters": {
                "type": "object",
                "properties": {"employee_id": {"type": "string"}},
                "required": ["employee_id"]
            }
        }
    ]

    @staticmethod
    def hris_get_departments() -> dict[str, Any]:
        return {
            "success": True,
            "departments": _VALID_DEPARTMENTS,
            "total": len(_VALID_DEPARTMENTS)
        }

    @staticmethod
    def hris_create_employee(
        full_name: str,
        personal_email: str,
        role: str,
        department: str,
        start_date: str,
        employment_type: str = "full_time",
        manager_name: str = "",
        compensation: float = 0.0,
    ) -> dict[str, Any]:
        # Check for duplicates
        for emp in _EMPLOYEE_DB.values():
            if emp["personal_email"] == personal_email:
                return {
                    "success": False,
                    "error": "DUPLICATE_EMPLOYEE",
                    "message": f"Employee with email {personal_email} already exists."
                }

        if department not in _VALID_DEPARTMENTS:
            return {
                "success": False,
                "error": "INVALID_DEPARTMENT",
                "message": f"Department '{department}' not found."
            }

        employee_id = f"EMP-{str(uuid.uuid4())[:8].upper()}"
        record = {
            "employee_id": employee_id,
            "full_name": full_name,
            "personal_email": personal_email,
            "role": role,
            "department": department,
            "start_date": start_date,
            "employment_type": employment_type,
            "manager_name": manager_name,
            # compensation stored internally but never returned in public fields
            "_compensation": compensation,
            "created_at": datetime.now().isoformat(),
            "status": "pending_start",
        }
        _EMPLOYEE_DB[employee_id] = record

        return {
            "success": True,
            "employee_id": employee_id,
            "full_name": full_name,
            "role": role,
            "department": department,
            "start_date": start_date,
            "employment_type": employment_type,
            "status": "pending_start",
            "message": f"Employee record created successfully. ID: {employee_id}"
        }

    @staticmethod
    def hris_get_employee(employee_id: str) -> dict[str, Any]:
        emp = _EMPLOYEE_DB.get(employee_id)
        if not emp:
            return {"success": False, "error": "NOT_FOUND"}
        # Never expose _compensation
        safe = {k: v for k, v in emp.items() if not k.startswith("_")}
        return {"success": True, "employee": safe}

    def dispatch(self, tool_name: str, params: dict) -> dict[str, Any]:
        """MCP dispatcher — routes tool calls to handlers."""
        handlers = {
            "hris_get_departments": lambda p: self.hris_get_departments(),
            "hris_create_employee": lambda p: self.hris_create_employee(**p),
            "hris_get_employee": lambda p: self.hris_get_employee(**p),
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return handler(params)
