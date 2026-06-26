# Smart Employee Onboarding Orchestrator

> Kaggle Capstone — 5-Day AI Agents: Intensive Vibe Coding Course with Google

An agentic AI pipeline that automates end-to-end employee onboarding using DAG orchestration, MCP tool integration, agent skills, zero ambient authority, and evaluation-driven development.

**28 tool calls. 4 skills. 0 human handoffs.**

---

## What It Does

Given a new hire's details, the agent automatically:

- ✅ Creates HR record + sends compliance documents (offer letter, W4, NDA)
- ✅ Provisions corporate email, GitHub, Slack, and software licenses (role-matched)
- ✅ Assigns a personalized training curriculum with deadlines and calendar sessions
- ✅ Briefs the hiring manager, schedules 30/60/90-day reviews, posts Slack welcome

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/onboarding-agent
cd onboarding-agent
pip install -r requirements.txt

# Run in mock mode (no API key needed — full pipeline, deterministic)
python3 kaggle_demo.py --mock

# Run with live Gemini API
export GEMINI_API_KEY="your_key_here"
python3 kaggle_demo.py
```

Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

Then open `dashboard/dashboard.html` in your browser to see the A2UI live dashboard.

---

## Architecture

```
OnboardingOrchestrator (DAG harness)
│
├── [Step 1] HR Intake          ← hris_create_employee, email_send_document
│       ↓ message_bus/hr_output.json
├── [Step 2] IT Provisioning    ← it_create_email, it_provision_github, it_provision_slack
│       ↓ message_bus/it_output.json  
├── [Step 3] Training Assignment← training_assign_course, calendar_schedule_session
│       ↓ message_bus/training_output.json
└── [Step 4] Manager Handoff    ← slack_post_message, email_send_document, calendar_schedule_session
        ↓ message_bus/onboarding_complete.json
```

## Project Structure

```
onboarding-agent/
├── agents.md                        # Global static context (always loaded)
├── orchestrator.py                  # DAG engine + MCP gateway + SkillRunner
├── kaggle_demo.py                   # Entry point — run this
├── requirements.txt
│
├── .agent-skills/                   # Progressive disclosure skill library
│   ├── hr/skill.md                  # HR Intake skill
│   ├── it/skill.md                  # IT Provisioning skill
│   ├── training/skill.md            # Training Assignment skill
│   ├── manager/skill.md             # Manager Handoff skill
│   └── */evals/cases.json           # 3 eval cases per skill (12 total)
│
├── mcp_tools/                       # Mock MCP tool servers
│   ├── hris.py                      # Mock Workday/BambooHR
│   ├── it_provisioning.py           # Mock IT systems
│   ├── slack.py                     # Mock Slack
│   ├── github.py                    # Mock GitHub
│   ├── calendar.py                  # Mock Google Calendar
│   └── email.py                     # Mock email
│
├── evals/
│   └── trajectory_scorer.py         # Trajectory scoring + Pass-to-K metric
│
├── message_bus/                     # Inter-skill file communication
│   └── *.json                       # Written at runtime
│
└── dashboard/
    └── dashboard.html               # A2UI live dashboard
```

## Course Concepts Demonstrated

| Day | Concept | Where |
|-----|---------|-------|
| Day 1 | Agentic Engineering vs Vibe Coding | Full pipeline + eval scorer |
| Day 2 | Agent = Model + Harness | `orchestrator.py` |
| Day 2 | MCP (standardized tool integration) | `mcp_tools/` — standard schemas + dispatch |
| Day 3 | 6 types of context | `agents.md` + `skill.md` + `message_bus/` |
| Day 3 | Progressive disclosure | SkillRunner loads only active skill's tools |
| Day 3 | Agent skills (not swarm) | `.agent-skills/` — 4 skills replace 4 sub-agents |
| Day 3 | Intelligent model routing | Flash for structured tasks, Pro for reasoning |
| Day 3 | Factory model / DAG | `OnboardingOrchestrator.DAG` |
| Day 4 | Zero ambient authority | `MCPToolRegistry.call()` — enforced at gateway |
| Day 4 | Trajectory recording | `TrajectoryRecord` + `message_bus/trajectory.json` |
| Day 5 | Spec-driven development | `skill.md` IS the spec |
| Day 5 | Evaluation-driven development | `evals/trajectory_scorer.py` |
| Day 5 | Pass-to-K metric | `TrajectoryScorer.pass_to_k()` |

## Evaluation Results

```
Cases passed:     10 / 11  (91%)
Pass-to-K (k=5):  62.1%   (production ready threshold: 50%)
Active context:   ~1,710 tokens  (vs ~15,000 without progressive disclosure)
Tool calls:       28 per full onboarding run
```

## Running on Kaggle

In a Kaggle notebook, add your API key as a Secret named `GEMINI_API_KEY`, then:

```python
import os
from kaggle_secrets import UserSecretsClient
os.environ["GEMINI_API_KEY"] = UserSecretsClient().get_secret("GEMINI_API_KEY")

exec(open("kaggle_demo.py").read())
```

Or run in mock mode (no key needed):
```python
import sys
sys.argv = ["kaggle_demo.py", "--mock"]
exec(open("kaggle_demo.py").read())
```

## License

MIT
