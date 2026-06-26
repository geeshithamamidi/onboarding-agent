"""
Kaggle Demo Script — Smart Employee Onboarding Orchestrator
============================================================
Kaggle 5-Day AI Agents: Intensive Vibe Coding Course with Google — Capstone

Run this file to see the full agent pipeline execute end-to-end.

Usage:
  export GEMINI_API_KEY="your_key_here"
  python kaggle_demo.py

Or in a Kaggle notebook:
  import os
  os.environ["GEMINI_API_KEY"] = "your_key"
  exec(open("kaggle_demo.py").read())

Course Concepts Demonstrated (Days 1-5):
  Day 1 — Vibe Coding vs Agentic Engineering: this uses full agentic engineering
           with evaluation, not just "vibe" prompt-and-hope.
  Day 2 — MCP: all tools follow the MCP pattern (standard schemas, dispatch layer,
           zero brittle wrappers). Swap mock for real by changing one line.
  Day 2 — Agent = Model + Harness: Gemini is 10% of the system; orchestrator/
           skill harness is 90%.
  Day 3 — Context Engineering: 6 types of context wired (instructions, knowledge,
           memory via file bus, examples in evals, tools, guardrails).
           Progressive disclosure: each skill loads only its 3-4 tools.
  Day 3 — Agent Skills: 4 skill.md files replace a swarm of sub-agents.
  Day 4 — Zero Ambient Authority: MCP gateway blocks cross-department tool access.
           Trajectory recording for full observability.
  Day 5 — Spec-Driven Development: skill.md files ARE the spec. Code is generated
           from specs, not written manually.
  Day 5 — Evaluation-Driven Development: trajectory scorer validates tool call
           sequence, not just final output.
"""

import os
import sys
import json
from datetime import date, timedelta
from pathlib import Path

# ─── Setup ─────────────────────────────────────────────────────────────────────

# Mock mode: runs full pipeline deterministically without any API calls.
# Usage:  python kaggle_demo.py --mock
#   OR:   MOCK_MODE=1 python kaggle_demo.py
MOCK_MODE = "--mock" in sys.argv or os.environ.get("MOCK_MODE", "") == "1"

print("=" * 65)
print("  SMART EMPLOYEE ONBOARDING ORCHESTRATOR")
print("  Kaggle Capstone | 5-Day AI Agents Course with Google")
print("=" * 65)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if MOCK_MODE:
    print(f"\n✓ Mode: MOCK (deterministic — no API calls)")
    print(f"  All real MCP tools execute; LLM decisions are scripted.")
    print(f"  Switch to live mode: remove --mock and set GEMINI_API_KEY.")
elif not GEMINI_API_KEY:
    print(f"\n⚠ No GEMINI_API_KEY found — running in mock mode automatically.")
    print(f"  To use live Gemini: export GEMINI_API_KEY='your_key'")
    MOCK_MODE = True
else:
    print(f"\n✓ Gemini API key loaded")
    print(f"✓ Model routing: gemini-2.0-flash-lite (HR/IT/Manager) + gemini-2.0-flash-lite (Training)")

# ─── Import & Run ──────────────────────────────────────────────────────────────

from orchestrator import OnboardingOrchestrator, NewHire
from evals.trajectory_scorer import TrajectoryScorer

# Define the new hire to onboard
hire = NewHire(
    full_name="Geesh Mamidi",
    personal_email="geeshithamamidi@gmail.com",
    role="Software Engineer",
    department="Engineering",
    start_date=(date.today() + timedelta(days=14)).strftime("%Y-%m-%d"),
    employment_type="full_time",
    manager_name="Priya Sharma",
    manager_email="priya.sharma@company.com",
    compensation=130000,  # HR-only, never passed to other skills
)

print(f"\n📋 New hire: {hire.full_name}")
print(f"   Role: {hire.role} | Dept: {hire.department}")
print(f"   Start date: {hire.start_date}")
print(f"\n📊 DAG: [HR Intake] → [IT Provisioning] → [Training] → [Manager Handoff]")
print(f"   File message bus: skills communicate via message_bus/*.json")
print(f"   Zero ambient authority: each skill sees only its permitted tools\n")

# ─── Run the Pipeline ──────────────────────────────────────────────────────────

orchestrator = OnboardingOrchestrator(gemini_api_key=GEMINI_API_KEY, mock=MOCK_MODE)
report = orchestrator.run(hire)

# ─── Print Summary ─────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("  PIPELINE COMPLETE — SUMMARY")
print("=" * 65)

if report.get("pipeline_status") == "complete":
    emp = report.get("employee", {})
    print(f"\n  Employee:       {emp.get('name')}")
    print(f"  Employee ID:    {emp.get('employee_id')}")
    print(f"  Corporate Email:{emp.get('corporate_email')}")
    print(f"  Start Date:     {emp.get('start_date')}")
    print(f"\n  Steps Completed: {len(report.get('steps_completed', []))}/4")
    for step in report.get("steps_completed", []):
        print(f"    ✓ {step}")
    print(f"\n  Duration:        {report.get('duration_seconds')}s")
    print(f"  Total tool calls:{report.get('trajectory_events')}")
else:
    print(f"\n  ✗ Pipeline failed: {report.get('failed_skill')}")
    print(f"  Error: {report.get('error')}")

# ─── Run Evaluation ────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("  EVALUATION-DRIVEN DEVELOPMENT — TRAJECTORY SCORING")
print("=" * 65)
print("\n  Evaluating actual tool call trajectory against expected patterns...")
print("  (60% trajectory weight + 40% output schema = combined score)\n")

scorer = TrajectoryScorer()
eval_report = scorer.run_full_evaluation()

# ─── Show File Outputs ─────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("  OUTPUT FILES (message_bus/)")
print("=" * 65)

bus = Path("message_bus")
for f in sorted(bus.glob("*.json")):
    size = f.stat().st_size
    print(f"  {f.name:40s} {size:6d} bytes")

print("\n  Open dashboard/dashboard.html in a browser to see the A2UI.")
print("\n  All course concepts demonstrated:")

concepts = [
    ("Day 1", "Agentic Engineering (not vibe coding) — evaluation + deterministic DAG"),
    ("Day 2", "MCP pattern — standardized tool dispatch, zero brittle wrappers"),
    ("Day 2", "Agent = Model (Gemini) + Harness (orchestrator.py)"),
    ("Day 3", "6 types of context + progressive disclosure (1,710 vs 15,000 tokens)"),
    ("Day 3", "Agent skills replacing multi-agent swarm (4 skill.md files)"),
    ("Day 3", "Intelligent model routing (Flash for simple, Pro for curriculum)"),
    ("Day 4", "Zero ambient authority — MCP gateway enforces cross-dept isolation"),
    ("Day 4", "Full trajectory observability (message_bus/trajectory.json)"),
    ("Day 5", "Spec-driven development — skill.md IS the spec"),
    ("Day 5", "Trajectory scoring (not output-only) — Pass-to-K metric"),
]

for day, concept in concepts:
    print(f"  [{day}] {concept}")

print("\n  Done.\n")
