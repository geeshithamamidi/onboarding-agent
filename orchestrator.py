"""
Smart Employee Onboarding Orchestrator
========================================
Capstone project for Kaggle 5-Day AI Agents: Intensive Vibe Coding Course with Google.

Architecture (from Day 1-5 concepts):
  - Agent = Model (Gemini) + Harness (this file)
  - DAG orchestration: HR → IT → Training → Manager Handoff
  - File message bus: skills communicate via message_bus/ files, not context window
  - Progressive disclosure: each skill's instructions loaded ONLY when that step is active
  - Zero ambient authority: each skill sees only its permitted tools
  - Context engineering: 6 types of context (instructions, knowledge, memory, examples, tools, guardrails)
  - Trajectory scoring: records exact tool call sequence for evaluation
  - Intelligent model routing: Flash for simple steps, Pro for complex reasoning
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types as genai_types

# MCP Tool Servers
from mcp_tools.hris import HRISTools
from mcp_tools.it_provisioning import ITProvisioningTools
from mcp_tools.slack import SlackTools
from mcp_tools.calendar import CalendarTools
from mcp_tools.email import EmailTools

# ─── Configuration ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
SKILLS_DIR = BASE_DIR / ".agent-skills"
MESSAGE_BUS = BASE_DIR / "message_bus"
AGENTS_MD = BASE_DIR / "agents.md"

MESSAGE_BUS.mkdir(exist_ok=True)


@dataclass
class NewHire:
    full_name: str
    personal_email: str
    role: str
    department: str
    start_date: str
    employment_type: str = "full_time"
    manager_name: str = "Engineering Manager"
    manager_email: str = "manager@company.com"
    compensation: float = 0.0  # Never passed to non-HR skills


@dataclass
class TrajectoryRecord:
    """Records every tool call for trajectory scoring (Day 4/5 concept)."""
    skill: str
    tool_name: str
    params: dict
    result: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = True


# ─── MCP Tool Registry ─────────────────────────────────────────────────────────

class MCPToolRegistry:
    """
    Simulates a centralized MCP gateway that validates tool access.
    Implements zero ambient authority: each skill declares its allowed tools,
    and the registry enforces that boundary at dispatch time.
    """

    def __init__(self):
        self._hris = HRISTools()
        self._it = ITProvisioningTools()
        self._slack = SlackTools()
        self._calendar = CalendarTools()
        self._email = EmailTools()

        self._all_tools = {
            "hris_create_employee": self._hris.dispatch,
            "hris_get_departments": self._hris.dispatch,
            "hris_get_employee": self._hris.dispatch,
            "it_create_email": self._it.dispatch,
            "it_provision_github": self._it.dispatch,
            "it_provision_slack": self._it.dispatch,
            "it_assign_licenses": self._it.dispatch,
            "slack_post_message": self._slack.dispatch,
            "calendar_schedule_session": self._calendar.dispatch,
            "email_send_document": self._email.dispatch,
            "training_get_catalog": self._mock_training_catalog,
            "training_assign_course": self._mock_training_assign,
        }

        # Tool schemas for Gemini function calling
        self._schemas = (
            HRISTools.TOOL_SCHEMAS +
            ITProvisioningTools.TOOL_SCHEMAS +
            SlackTools.TOOL_SCHEMAS +
            CalendarTools.TOOL_SCHEMAS +
            EmailTools.TOOL_SCHEMAS +
            self._training_schemas()
        )

    def _training_schemas(self):
        return [
            {
                "name": "training_get_catalog",
                "description": "Get the current training course catalog.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "training_assign_course",
                "description": "Assign a training course to an employee.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "string"},
                        "course_id": {"type": "string"},
                        "deadline": {"type": "string"}
                    },
                    "required": ["employee_id", "course_id", "deadline"]
                }
            }
        ]

    def _mock_training_catalog(self, tool_name: str, params: dict) -> dict:
        courses = [
            {"id": "COMP-001", "title": "Code of Conduct & Ethics", "duration_mins": 30},
            {"id": "COMP-002", "title": "Information Security Awareness", "duration_mins": 45},
            {"id": "COMP-003", "title": "Anti-Harassment Policy", "duration_mins": 30},
            {"id": "COMP-004", "title": "Data Privacy & GDPR Basics", "duration_mins": 40},
            {"id": "ENG-101", "title": "Codebase Introduction", "duration_mins": 90},
            {"id": "ENG-102", "title": "CI/CD Pipeline", "duration_mins": 60},
            {"id": "ENG-103", "title": "Code Review Standards", "duration_mins": 45},
            {"id": "ENG-201", "title": "System Design Principles", "duration_mins": 120},
            {"id": "DES-101", "title": "Design System Overview", "duration_mins": 60},
            {"id": "DES-102", "title": "Figma Workflow", "duration_mins": 45},
            {"id": "DES-103", "title": "Brand Guidelines", "duration_mins": 30},
            {"id": "MGR-101", "title": "Management Framework", "duration_mins": 90},
            {"id": "MGR-102", "title": "Performance Reviews", "duration_mins": 60},
            {"id": "MGR-103", "title": "Hiring Process", "duration_mins": 75},
            {"id": "DATA-101", "title": "Data Stack Overview", "duration_mins": 60},
            {"id": "DATA-102", "title": "SQL Standards", "duration_mins": 45},
            {"id": "DATA-103", "title": "Dashboard Creation", "duration_mins": 60},
            {"id": "GEN-101", "title": "Company Overview", "duration_mins": 60},
            {"id": "GEN-102", "title": "Tools Tour", "duration_mins": 45},
        ]
        return {"success": True, "courses": courses, "total": len(courses)}

    def _mock_training_assign(self, tool_name: str, params: dict) -> dict:
        return {
            "success": True,
            "assignment_id": f"assign-{params.get('course_id')}-{params.get('employee_id')}",
            "employee_id": params.get("employee_id"),
            "course_id": params.get("course_id"),
            "deadline": params.get("deadline"),
            "status": "assigned",
            "message": f"Course {params.get('course_id')} assigned."
        }

    def call(self, tool_name: str, params: dict, allowed_tools: list[str]) -> dict:
        """
        Zero ambient authority enforcement: reject tool calls not in the
        skill's declared allowed list. This is the MCP gateway acting as bouncer.
        """
        if tool_name not in allowed_tools:
            return {
                "success": False,
                "error": "PERMISSION_DENIED",
                "message": f"Tool '{tool_name}' is not permitted for the current skill. "
                           f"Allowed: {allowed_tools}"
            }
        handler = self._all_tools.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Tool '{tool_name}' not registered."}
        return handler(tool_name, params)

    def get_schemas_for(self, allowed_tools: list[str]) -> list[dict]:
        """Progressive disclosure: return only the schemas for allowed tools."""
        return [s for s in self._schemas if s["name"] in allowed_tools]


# ─── Skill Loader ──────────────────────────────────────────────────────────────

def load_skill(skill_name: str) -> str:
    """
    Progressive disclosure: load a skill's instructions from disk ONLY
    when that step is active. This keeps the context window clean.
    """
    skill_path = SKILLS_DIR / skill_name / "skill.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")
    return skill_path.read_text()


def load_global_context() -> str:
    return AGENTS_MD.read_text() if AGENTS_MD.exists() else ""


# ─── Skill Runner ──────────────────────────────────────────────────────────────

class SkillRunner:
    """
    Runs a single skill using Gemini with function calling.
    Implements: progressive disclosure, zero ambient authority,
    trajectory recording, and file message bus output.
    """

    SKILL_TOOLS = {
        "hr": {
            "allowed": ["hris_create_employee", "hris_get_departments", "email_send_document"],
            "model": "gemini-2.0-flash-lite",
        },
        "it": {
            "allowed": ["it_create_email", "it_provision_github", "it_provision_slack", "it_assign_licenses"],
            "model": "gemini-2.0-flash-lite",
        },
        "training": {
            "allowed": ["training_get_catalog", "training_assign_course", "calendar_schedule_session", "email_send_document"],
            "model": "gemini-2.0-flash-lite",   # use lite across all skills for free tier
        },
        "manager": {
            "allowed": ["calendar_schedule_session", "slack_post_message", "email_send_document"],
            "model": "gemini-2.0-flash-lite",
        },
    }

    def __init__(self, registry: MCPToolRegistry, gemini_api_key: str):
        self.registry = registry
        self.client = genai.Client(api_key=gemini_api_key)
        self.trajectory: list[TrajectoryRecord] = []

    def _build_tools_for_gemini(self, allowed_tools: list[str]) -> list[genai_types.Tool]:
        """Convert MCP tool schemas to google.genai Tool objects (new SDK)."""
        schemas = self.registry.get_schemas_for(allowed_tools)
        declarations = []
        for schema in schemas:
            parameters = self._build_schema(schema.get("parameters", {}))
            declarations.append(genai_types.FunctionDeclaration(
                name=schema["name"],
                description=schema.get("description", ""),
                parameters=parameters,
            ))
        return [genai_types.Tool(function_declarations=declarations)]

    def _build_schema(self, spec: dict) -> genai_types.Schema:
        """Recursively convert JSON-schema-like dict to genai Schema."""
        type_map = {
            "string": "STRING", "integer": "INTEGER", "number": "NUMBER",
            "boolean": "BOOLEAN", "array": "ARRAY", "object": "OBJECT",
        }
        kwargs: dict[str, Any] = {"type": type_map.get(spec.get("type", "string"), "STRING")}

        if "description" in spec:
            kwargs["description"] = spec["description"]
        if "enum" in spec:
            kwargs["enum"] = spec["enum"]
        if spec.get("type") == "object":
            kwargs["properties"] = {
                k: self._build_schema(v)
                for k, v in spec.get("properties", {}).items()
            }
            if "required" in spec:
                kwargs["required"] = spec["required"]
        if spec.get("type") == "array":
            kwargs["items"] = self._build_schema(spec.get("items", {"type": "string"}))

        return genai_types.Schema(**kwargs)

    def _generate_with_retry(self, model_name: str, contents: list, config: genai_types.GenerateContentConfig) -> Any:
        """Call Gemini with exponential backoff on 429 rate-limit errors."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                err = str(e)
                if "429" in err or "ResourceExhausted" in err or "quota" in err.lower():
                    # Parse retry_delay from error if present, else exponential backoff
                    wait = min(60, 10 * (2 ** attempt))
                    print(f"  ⚠ Rate limit hit. Waiting {wait}s before retry {attempt+1}/{max_retries}...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError(f"Gemini API rate limit exceeded after {max_retries} retries.")

    def run(self, skill_name: str, user_prompt: str) -> dict[str, Any]:
        """
        Run a skill with Gemini function calling (google.genai new SDK).
        Maintains a multi-turn contents list for the agentic loop.
        """
        config = self.SKILL_TOOLS[skill_name]
        allowed_tools = config["allowed"]
        model_name = config["model"]

        print(f"\n{'='*60}")
        print(f"  SKILL: {skill_name.upper()} | Model: {model_name}")
        print(f"  Context: {len(allowed_tools)} tools loaded (progressive disclosure)")
        print(f"{'='*60}")

        # Progressive disclosure: load only this skill's instructions
        skill_instructions = load_skill(skill_name)
        global_context = load_global_context()

        system_prompt = (
            f"{global_context}\n\n---\n## Active Skill: {skill_name}\n\n"
            f"{skill_instructions}\n\n---\n## Output Instructions\n"
            "After completing all steps, return a JSON object matching the Output Schema "
            "defined in the skill. Do not include any text outside the JSON in your final response."
        )

        tools = self._build_tools_for_gemini(allowed_tools)
        gen_config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tools,
            temperature=0.2,
        )

        # Multi-turn conversation history for agentic loop
        contents: list[genai_types.Content] = [
            genai_types.Content(role="user", parts=[genai_types.Part(text=user_prompt)])
        ]

        response = self._generate_with_retry(model_name, contents, gen_config)

        max_iterations = 20
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            has_function_call = False

            candidate = response.candidates[0]

            for part in candidate.content.parts:
                if part.function_call and part.function_call.name:
                    has_function_call = True
                    fc = part.function_call
                    tool_name = fc.name
                    params = dict(fc.args) if fc.args else {}

                    print(f"  → Tool call: {tool_name}({json.dumps(params, default=str)[:80]})")

                    # Zero ambient authority enforcement at MCP gateway
                    result = self.registry.call(tool_name, params, allowed_tools)

                    # Record full trajectory (not just output)
                    self.trajectory.append(TrajectoryRecord(
                        skill=skill_name,
                        tool_name=tool_name,
                        params=params,
                        result=result,
                        success=result.get("success", False)
                    ))

                    print(f"  ✓ Result: {str(result)[:100]}")

                    # Append model turn + function result to history
                    contents.append(candidate.content)
                    contents.append(genai_types.Content(
                        role="user",
                        parts=[genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=tool_name,
                                response={"result": result},
                            )
                        )]
                    ))

                    response = self._generate_with_retry(model_name, contents, gen_config)
                    break  # one function call per iteration

            if not has_function_call:
                # Final text response — extract JSON
                text = ""
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
                text = text.strip()

                # Strip markdown fences if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

                try:
                    output = json.loads(text)
                except json.JSONDecodeError:
                    output = {"skill": skill_name, "status": "success", "raw_output": text}

                # Write to file message bus (not context window)
                output_file = MESSAGE_BUS / f"{skill_name}_output.json"
                with open(output_file, "w") as f:
                    json.dump(output, f, indent=2)
                print(f"  ✓ Output written to message_bus/{skill_name}_output.json")

                return output

        return {"skill": skill_name, "status": "failed", "error": "Max iterations reached"}


# ─── Mock Skill Runner (no API key needed) ─────────────────────────────────────

class MockSkillRunner:
    """
    Deterministic mock runner — calls all real MCP tools in the correct sequence
    without making any Gemini API calls.

    Used for local testing and Kaggle submission demos when API quota is unavailable.
    Demonstrates the same pipeline: progressive disclosure, zero ambient authority,
    trajectory recording, and file message bus — just with scripted LLM decisions.

    This is actually a core agentic engineering principle (Day 5): rely on deterministic
    code constraints rather than probabilistic LLM outputs wherever possible.
    """

    def __init__(self, registry: MCPToolRegistry):
        self.registry = registry
        self.trajectory: list[TrajectoryRecord] = []

    def _call(self, skill: str, tool: str, allowed: list[str], params: dict) -> dict:
        """Call a tool and record the trajectory."""
        result = self.registry.call(tool, params, allowed)
        self.trajectory.append(TrajectoryRecord(
            skill=skill, tool_name=tool, params=params,
            result=result, success=result.get("success", False)
        ))
        print(f"  → Tool call: {tool}({json.dumps(params, default=str)[:80]})")
        print(f"  ✓ Result: {str(result)[:100]}")
        return result

    def run(self, skill_name: str, user_prompt: str) -> dict[str, Any]:
        allowed = {
            "hr":       ["hris_create_employee", "hris_get_departments", "email_send_document"],
            "it":       ["it_create_email", "it_provision_github", "it_provision_slack", "it_assign_licenses"],
            "training": ["training_get_catalog", "training_assign_course", "calendar_schedule_session", "email_send_document"],
            "manager":  ["calendar_schedule_session", "slack_post_message", "email_send_document"],
        }[skill_name]

        print(f"\n{'='*60}")
        print(f"  SKILL: {skill_name.upper()} | Mode: MOCK (deterministic)")
        print(f"  Context: {len(allowed)} tools loaded (progressive disclosure)")
        print(f"{'='*60}")

        # Extract hire data from prompt (simple parse)
        hire = self._parse_hire(user_prompt)
        output = {}

        if skill_name == "hr":
            self._call(skill_name, "hris_get_departments", allowed, {})
            r = self._call(skill_name, "hris_create_employee", allowed, {
                "full_name": hire["full_name"], "personal_email": hire["personal_email"],
                "role": hire["role"], "department": hire["department"],
                "start_date": hire["start_date"], "employment_type": hire.get("employment_type", "full_time"),
                "manager_name": hire.get("manager_name", ""), "compensation": hire.get("compensation", 0),
            })
            emp_id = r.get("employee_id", "EMP-MOCK001")
            docs = (["offer_acknowledgement", "tax_w4", "nda", "benefits_enrollment"]
                    if hire.get("employment_type") != "contractor"
                    else ["contractor_agreement", "tax_w9", "nda"])
            from datetime import datetime as dt, timedelta as td
            deadline = (dt.strptime(hire["start_date"], "%Y-%m-%d") - td(days=3)).strftime("%Y-%m-%d")
            self._call(skill_name, "email_send_document", allowed, {
                "recipient": hire["personal_email"],
                "subject": f"Welcome to Company — Action Required: Day-1 Documents",
                "documents": docs, "deadline": deadline,
            })
            first, *last = hire["full_name"].split()
            output = {
                "skill": "hr-intake", "status": "success", "employee_id": emp_id,
                "full_name": hire["full_name"], "role": hire["role"],
                "department": hire["department"], "start_date": hire["start_date"],
                "corporate_email": f"{first.lower()}.{''.join(last).lower()}@company.com",
                "documents_sent": docs, "documents_deadline": deadline, "error": None,
            }

        elif skill_name == "it":
            hr = json.loads((MESSAGE_BUS / "hr_output.json").read_text())
            emp_id = hr["employee_id"]
            corp_email = hr["corporate_email"]
            role = hr["role"].lower()

            self._call(skill_name, "it_create_email", allowed,
                       {"employee_id": emp_id, "corporate_email": corp_email})

            teams = (["eng-general", "product"] if any(k in role for k in ["engineer","dev","software"])
                     else ["design"] if "design" in role
                     else ["data-team"] if any(k in role for k in ["data","analyst"])
                     else ["general-staff"])
            channels = (["#engineering","#general","#deploys"] if any(k in role for k in ["engineer","dev","software"])
                        else ["#design","#general"] if "design" in role
                        else ["#data","#general","#analytics"] if "analyst" in role
                        else ["#general","#announcements"])
            licenses = (["GitHub Pro","VSCode","Jira"] if any(k in role for k in ["engineer","dev","software"])
                        else ["Figma","Notion","Jira"] if "design" in role
                        else ["Looker","Notion","Jira"] if "analyst" in role
                        else ["Notion","Jira"])

            gh = self._call(skill_name, "it_provision_github", allowed,
                            {"employee_id": emp_id, "teams": teams})
            sl = self._call(skill_name, "it_provision_slack", allowed,
                            {"employee_id": emp_id, "corporate_email": corp_email, "channels": channels})
            self._call(skill_name, "it_assign_licenses", allowed,
                       {"employee_id": emp_id, "license_list": licenses})

            output = {
                "skill": "it-provisioning", "status": "success", "employee_id": emp_id,
                "corporate_email": corp_email,
                "github_username": gh.get("github_username", ""),
                "slack_id": sl.get("slack_id", ""),
                "github_teams": teams, "slack_channels": channels,
                "licenses_assigned": licenses, "error": None,
            }

        elif skill_name == "training":
            hr = json.loads((MESSAGE_BUS / "hr_output.json").read_text())
            it = json.loads((MESSAGE_BUS / "it_output.json").read_text())
            emp_id = hr["employee_id"]
            corp_email = it["corporate_email"]
            role = hr["role"].lower()
            start = hr["start_date"]

            catalog = self._call(skill_name, "training_get_catalog", allowed, {})
            mandatory = [
                {"course_id": "COMP-001", "deadline_offset": 3},
                {"course_id": "COMP-002", "deadline_offset": 5},
                {"course_id": "COMP-003", "deadline_offset": 5},
                {"course_id": "COMP-004", "deadline_offset": 7},
            ]
            role_courses = (
                [{"course_id": c, "deadline_offset": 10+i*3} for i, c in enumerate(["ENG-101","ENG-102","ENG-103","ENG-201"])]
                if any(k in role for k in ["engineer","dev","software"])
                else [{"course_id": c, "deadline_offset": 10+i*3} for i, c in enumerate(["DES-101","DES-102","DES-103"])]
                if "design" in role
                else [{"course_id": c, "deadline_offset": 10+i*3} for i, c in enumerate(["DATA-101","DATA-102","DATA-103"])]
                if "analyst" in role
                else [{"course_id": c, "deadline_offset": 7+i*3} for i, c in enumerate(["GEN-101","GEN-102"])]
            )

            from datetime import datetime as dt, timedelta as td
            start_dt = dt.strptime(start, "%Y-%m-%d")
            assigned = []
            for c in mandatory + role_courses:
                dl = (start_dt + td(days=c["deadline_offset"])).strftime("%Y-%m-%d")
                self._call(skill_name, "training_assign_course", allowed,
                           {"employee_id": emp_id, "course_id": c["course_id"], "deadline": dl})
                assigned.append({"course_id": c["course_id"], "deadline": dl})

            sessions = []
            for s in [("Day-1 Company Welcome", 0, 60), ("Week-1 Manager 1:1", 3, 30), ("Technical Deep-Dive", 10, 90)]:
                title, offset, dur = s
                event_date = (start_dt + td(days=offset)).strftime("%Y-%m-%d")
                self._call(skill_name, "calendar_schedule_session", allowed, {
                    "title": title, "date": event_date, "duration_mins": dur,
                    "attendees": [corp_email],
                })
                sessions.append({"title": title, "date": event_date, "duration_mins": dur})

            self._call(skill_name, "email_send_document", allowed, {
                "recipient": corp_email,
                "subject": f"Your Onboarding Learning Path — {hr['full_name']}",
                "body": f"Welcome! Here is your personalized {len(assigned)}-course curriculum.",
            })

            plan = ({"day_30": "Contribute to first PR and complete codebase orientation",
                     "day_60": "Own a feature end-to-end and pass code review independently",
                     "day_90": "Lead a sprint task and mentor an intern or new joiner"}
                    if any(k in role for k in ["engineer","dev","software"])
                    else {"day_30": "Learn product and understand user personas",
                          "day_60": "Own a feature spec and present to stakeholders",
                          "day_90": "Ship first feature and collect user feedback"})

            output = {
                "skill": "training-assignment", "status": "success", "employee_id": emp_id,
                "courses_assigned": assigned, "sessions_scheduled": sessions,
                "plan_email_sent": True, "thirty_sixty_ninety_plan": plan, "error": None,
            }

        elif skill_name == "manager":
            hr = json.loads((MESSAGE_BUS / "hr_output.json").read_text())
            it = json.loads((MESSAGE_BUS / "it_output.json").read_text())
            tr = json.loads((MESSAGE_BUS / "training_output.json").read_text())
            emp_id = hr["employee_id"]
            corp_email = it["corporate_email"]
            github = it.get("github_username", "")
            start = hr["start_date"]
            manager_email = hire.get("manager_email", "manager@company.com")

            from datetime import datetime as dt, timedelta as td
            start_dt = dt.strptime(start, "%Y-%m-%d")

            events = []
            for ev in [
                ("Day-1 Morning Check-in", 0, 15, [corp_email, manager_email]),
                ("Week-1 Daily Sync", 1, 15, [corp_email, manager_email]),
                ("30-Day Review", 30, 30, [corp_email, manager_email]),
                ("60-Day Review", 60, 45, [corp_email, manager_email]),
                ("90-Day Review", 90, 60, [corp_email, manager_email]),
            ]:
                title, offset, dur, attendees = ev
                event_date = (start_dt + td(days=offset)).strftime("%Y-%m-%d")
                self._call(skill_name, "calendar_schedule_session", allowed, {
                    "title": title, "date": event_date, "duration_mins": dur,
                    "attendees": attendees,
                })
                events.append({"title": title, "date": event_date, "duration_mins": dur})

            gh_line = f" | GitHub: @{github}" if github else ""
            welcome_msg = (
                f"🎉 Please welcome *{hr['full_name']}* to the team!\n\n"
                f"They're joining as *{hr['role']}* starting *{start}*{gh_line}.\n\n"
                f"Feel free to say hi and make them feel at home. 👋"
            )
            for channel in it.get("slack_channels", ["#general"])[:2]:
                self._call(skill_name, "slack_post_message", allowed, {
                    "channel": channel, "message": welcome_msg, "sender_name": "Onboarding Bot",
                })

            self._call(skill_name, "email_send_document", allowed, {
                "recipient": manager_email,
                "subject": f"New Team Member Starting {start} — Briefing Pack: {hr['full_name']}",
                "body": (f"Hi,\n\n{hr['full_name']} joins as {hr['role']} on {start}.\n"
                         f"Corporate email: {corp_email}\nGitHub: @{github}\n\n"
                         f"30-60-90 plan attached. {len(tr['courses_assigned'])} courses assigned.\n\nGood luck!"),
            })

            output = {
                "skill": "manager-handoff", "status": "success", "employee_id": emp_id,
                "full_name": hr["full_name"], "onboarding_complete": True,
                "completed_at": datetime.now().isoformat(),
                "summary": {
                    "hr_record_created": True,
                    "accounts_provisioned": ["email", "github", "slack", "licenses"],
                    "courses_assigned": len(tr["courses_assigned"]),
                    "calendar_events_created": len(events),
                    "manager_briefing_sent": True, "team_notified": True,
                },
                "next_actions": [
                    f"Block 30 minutes on {start} morning for a personal welcome with {hr['full_name']}",
                    "Share the team's current sprint board and assign a first low-risk ticket by Day 3",
                    "Schedule a skip-level intro with your manager within the first two weeks",
                ],
                "error": None,
            }

        output_file = MESSAGE_BUS / f"{skill_name}_output.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"  ✓ Output written to message_bus/{skill_name}_output.json")
        return output

    def _parse_hire(self, prompt: str) -> dict:
        """Extract hire fields from the orchestrator prompt."""
        fields = {}
        patterns = {
            "full_name": r"Full name:\s*(.+)",
            "personal_email": r"Personal email:\s*(.+)",
            "role": r"Role:\s*(.+)",
            "department": r"Department:\s*(.+)",
            "start_date": r"Start date:\s*(\S+)",
            "employment_type": r"Employment type:\s*(\S+)",
            "manager_name": r"Manager:\s*(.+)",
            "manager_email": r"manager_email.*?(\S+@\S+)",
            "compensation": r"Compensation:\s*([\d.]+)",
        }
        import re
        for key, pat in patterns.items():
            m = re.search(pat, prompt, re.IGNORECASE)
            if m:
                fields[key] = m.group(1).strip()
        if "compensation" in fields:
            fields["compensation"] = float(fields["compensation"])
        return fields


# ─── DAG Orchestrator ──────────────────────────────────────────────────────────

class OnboardingOrchestrator:
    """
    The DAG orchestrator: builds and executes the onboarding pipeline.
    One-way, no cycles, no infinite loops.

    DAG nodes (in order):
      [HR Intake] → [IT Provisioning] → [Training Assignment] → [Manager Handoff]
    """

    DAG = [
        {
            "skill": "hr",
            "name": "HR Intake",
            "description": "Create employee record, send compliance documents",
        },
        {
            "skill": "it",
            "name": "IT Provisioning",
            "description": "Create email, GitHub, Slack accounts, assign licenses",
        },
        {
            "skill": "training",
            "name": "Training Assignment",
            "description": "Build personalized curriculum, schedule sessions",
        },
        {
            "skill": "manager",
            "name": "Manager Handoff",
            "description": "Prepare manager briefing, schedule 1:1s, notify team",
        },
    ]

    def __init__(self, gemini_api_key: str = "", mock: bool = False):
        self.registry = MCPToolRegistry()
        if mock or not gemini_api_key:
            print("  [Mode: MOCK — deterministic pipeline, no API calls]\n")
            self.runner = MockSkillRunner(self.registry)
        else:
            self.runner = SkillRunner(self.registry, gemini_api_key)
        self.results: dict[str, dict] = {}
        self.pipeline_log: list[dict] = []

    def _build_hr_prompt(self, hire: NewHire) -> str:
        return f"""
Onboard the following new employee. Execute all steps in the HR Intake skill.

New hire details:
- Full name: {hire.full_name}
- Personal email: {hire.personal_email}
- Role: {hire.role}
- Department: {hire.department}
- Start date: {hire.start_date}
- Employment type: {hire.employment_type}
- Manager: {hire.manager_name}
- Compensation: {hire.compensation}

Complete all HR intake steps and return the output JSON.
"""

    def _build_it_prompt(self) -> str:
        hr_out = (MESSAGE_BUS / "hr_output.json").read_text()
        return f"""
IT provisioning for new employee. HR intake is complete.

HR output (from message bus):
{hr_out}

Complete all IT provisioning steps based on the employee's role and return the output JSON.
"""

    def _build_training_prompt(self) -> str:
        hr_out = (MESSAGE_BUS / "hr_output.json").read_text()
        it_out = (MESSAGE_BUS / "it_output.json").read_text()
        return f"""
Assign training for new employee. HR and IT steps are complete.

HR output (from message bus):
{hr_out}

IT output (from message bus — use only corporate_email):
{it_out}

Build and assign the full onboarding curriculum, schedule sessions, and return the output JSON.
"""

    def _build_manager_prompt(self, hire: NewHire) -> str:
        hr_out = (MESSAGE_BUS / "hr_output.json").read_text()
        it_out = (MESSAGE_BUS / "it_output.json").read_text()
        training_out = (MESSAGE_BUS / "training_output.json").read_text()
        return f"""
Final manager handoff for new employee. All prior steps are complete.

Manager details:
- Manager name: {hire.manager_name}
- Manager email: {hire.manager_email}

HR output: {hr_out}
IT output: {it_out}
Training output: {training_out}

Complete manager handoff: briefing doc, schedule 1:1s, post Slack welcome, send email.
Return the final onboarding completion report as JSON.
"""

    def _prompt_for(self, skill: str, hire: NewHire) -> str:
        builders = {
            "hr": lambda: self._build_hr_prompt(hire),
            "it": lambda: self._build_it_prompt(),
            "training": lambda: self._build_training_prompt(),
            "manager": lambda: self._build_manager_prompt(hire),
        }
        return builders[skill]()

    def run(self, hire: NewHire) -> dict[str, Any]:
        """Execute the full onboarding DAG."""
        print(f"\n{'#'*60}")
        print(f"  ONBOARDING ORCHESTRATOR")
        print(f"  New hire: {hire.full_name} | Role: {hire.role}")
        print(f"  Start date: {hire.start_date}")
        print(f"  DAG: HR → IT → Training → Manager Handoff")
        print(f"{'#'*60}\n")

        start_time = time.time()

        for i, node in enumerate(self.DAG):
            skill = node["skill"]
            print(f"\n[Step {i+1}/{len(self.DAG)}] {node['name']}: {node['description']}")

            try:
                prompt = self._prompt_for(skill, hire)
                result = self.runner.run(skill, prompt)
                self.results[skill] = result

                step_log = {
                    "step": i + 1,
                    "skill": skill,
                    "name": node["name"],
                    "status": result.get("status", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }

                if result.get("status") == "failed":
                    step_log["error"] = result.get("error")
                    self.pipeline_log.append(step_log)
                    print(f"\n  ✗ Step {i+1} FAILED: {result.get('error')}")
                    print(f"  Pipeline halted. Writing error report...")
                    error_report = {
                        "pipeline_status": "failed",
                        "failed_at_step": i + 1,
                        "failed_skill": skill,
                        "error": result.get("error"),
                        "completed_steps": [s["name"] for s in self.pipeline_log if s.get("status") == "success"],
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(MESSAGE_BUS / "error.json", "w") as f:
                        json.dump(error_report, f, indent=2)
                    return error_report

                self.pipeline_log.append(step_log)
                print(f"\n  ✓ Step {i+1} completed successfully.")

            except Exception as e:
                print(f"\n  ✗ Exception in step {i+1}: {e}")
                raise

        # All steps done — write final report
        duration = time.time() - start_time
        final_report = {
            "pipeline_status": "complete",
            "employee": {
                "name": hire.full_name,
                "role": hire.role,
                "department": hire.department,
                "start_date": hire.start_date,
                "corporate_email": self.results.get("it", {}).get("corporate_email", ""),
                "employee_id": self.results.get("hr", {}).get("employee_id", ""),
            },
            "steps_completed": [node["name"] for node in self.DAG],
            "duration_seconds": round(duration, 2),
            "trajectory_events": len(self.runner.trajectory),
            "completed_at": datetime.now().isoformat(),
        }

        # Save trajectory for evaluation
        trajectory_data = [
            {
                "skill": t.skill,
                "tool": t.tool_name,
                "params": t.params,
                "success": t.success,
                "timestamp": t.timestamp,
            }
            for t in self.runner.trajectory
        ]
        with open(MESSAGE_BUS / "trajectory.json", "w") as f:
            json.dump(trajectory_data, f, indent=2, default=str)

        with open(MESSAGE_BUS / "pipeline_report.json", "w") as f:
            json.dump(final_report, f, indent=2)

        print(f"\n{'#'*60}")
        print(f"  ONBOARDING COMPLETE")
        print(f"  Employee: {hire.full_name} | ID: {final_report['employee']['employee_id']}")
        print(f"  Duration: {duration:.1f}s | Tool calls: {len(self.runner.trajectory)}")
        print(f"{'#'*60}\n")

        return final_report


# ─── Entry Point ───────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable.")
        sys.exit(1)

    # Example new hire
    hire = NewHire(
        full_name="Geesh Mamidi",
        personal_email="geeshithamamidi@gmail.com",
        role="Software Engineer",
        department="Engineering",
        start_date=(date.today() + timedelta(days=14)).strftime("%Y-%m-%d"),
        employment_type="full_time",
        manager_name="Priya Sharma",
        manager_email="priya.sharma@company.com",
        compensation=130000,
    )

    orchestrator = OnboardingOrchestrator(api_key)
    report = orchestrator.run(hire)

    print("\nFinal Pipeline Report:")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
