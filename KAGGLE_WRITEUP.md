# Smart Employee Onboarding Orchestrator

**Subtitle:** An agentic AI system that automates end-to-end employee onboarding using DAG orchestration, MCP tool integration, agent skills, and evaluation-driven development — applying every core concept from the 5-Day AI Agents course.

**Track:** Agents for Business

---

## The Problem

Every company onboards new employees the same way: HR sends emails, IT creates accounts manually, someone remembers to assign training, and a manager scrambles to prepare for Day 1. This process takes 3–5 business days, involves 4+ departments, and fails in predictable ways — the wrong documents get sent, accounts get provisioned with too many permissions, training gets skipped, or the manager isn't briefed until the morning the new hire walks in.

This is exactly the kind of repetitive, multi-step, cross-system workflow that agentic AI is built for.

---

## The Solution

The Smart Employee Onboarding Orchestrator is a production-grade multi-skill agent pipeline that automates the entire onboarding process in seconds, not days.

Given a new hire's name, role, department, and start date, the system:

1. Creates their official HR record and dispatches compliance documents
2. Provisions corporate email, GitHub, Slack, and software licenses based on role
3. Assigns a personalized training curriculum with deadlines and live sessions
4. Briefs the hiring manager, schedules 30/60/90-day reviews, and posts a Slack welcome

The pipeline runs end-to-end with 28 tool calls across 4 specialist skills, zero human intervention, and a full trajectory audit log for evaluation and compliance.

---

## Architecture: Agent = Model + Harness

The most important lesson from Day 2 of the course is that the foundation model is only ~10% of what makes an agent work. The other 90% is the harness — the scaffolding that prevents raw model intelligence from "wandering off a cliff."

This project implements that equation literally:

```
OnboardingOrchestrator (harness)
├── DAG engine              ← one-way, no cycles, no infinite loops
├── MCPToolRegistry         ← centralized gateway, zero ambient authority
├── SkillRunner / MockRunner← progressive disclosure, trajectory recording
└── File message bus        ← inter-skill communication without context pollution

Gemini API (model)
└── gemini-2.0-flash / gemini-2.5-flash via google-genai SDK
```

### DAG Orchestration

The pipeline is structured as a directed acyclic graph (DAG) — a concept from Day 3's factory model. Each node is a specialist skill that runs, writes its output to the file message bus, and hands off to the next node. No skill can loop back, and failure at any node halts the pipeline and writes an error report rather than allowing corrupted data to propagate.

```
[HR Intake] → [IT Provisioning] → [Training Assignment] → [Manager Handoff]
     ↓               ↓                    ↓                      ↓
hr_output.json  it_output.json   training_output.json   onboarding_complete.json
```

---

## Key Course Concepts Applied

### Context Engineering (Day 3)

The system implements all six types of context from the course:

- **Instructions** — `agents.md` defines the global persona, zero ambient authority rules, and DAG policy. Always loaded, never changes.
- **Knowledge** — each `skill.md` contains domain-specific procedural instructions for that department.
- **Memory** — the file message bus (`message_bus/*.json`) stores inter-skill state without polluting the context window.
- **Examples** — `evals/cases.json` files contain 3 evaluation cases per skill with expected trajectories.
- **Tools** — each skill declares exactly 3–4 allowed tools; the MCP gateway enforces this at dispatch time.
- **Guardrails** — embedded in each `skill.md` (e.g., "never expose compensation to non-HR skills").

**Progressive disclosure** is the key design pattern: rather than loading all 12 tool schemas and 4 skill instruction sets into every call, the system loads only the active skill's instructions and tools at each DAG node. This compresses active context from ~15,000 tokens to ~1,710 tokens — an 88% reduction — keeping the model sharp and reducing token cost.

### Agent Skills (Day 3)

Instead of building a swarm of sub-agents (a manager agent routing to HR agent, IT agent, etc.), the project uses 4 agent skill files that a single orchestrator loads on demand. Each `skill.md` defines:

- When to activate (trigger description)
- What tools are permitted (enforced by the MCP gateway)
- Step-by-step execution instructions
- Input/output JSON schemas
- Guardrails specific to that department

This approach is far simpler to maintain than a multi-agent swarm. Adding a new department means adding one folder with one `skill.md` — no new agents, no new routing logic, no new deployments.

### MCP (Model Context Protocol) — Day 2

All 6 tool integrations (HRIS, IT provisioning, Slack, GitHub, Calendar, Email) follow the MCP pattern: each has a standard JSON schema declaration and a dispatch method. The orchestrator calls tools through a centralized `MCPToolRegistry` that acts as the MCP gateway.

This means swapping a mock tool for a real one (e.g., replacing mock Slack with real Slack MCP server) requires zero changes to the agent logic — only the tool registration. The NxM integration problem collapses to N+M because all tools speak the same interface.

### Zero Ambient Authority (Day 4)

The MCP gateway enforces a strict permission model at runtime: if a skill's `allowed_tools` list does not contain a requested tool, the call is rejected with `PERMISSION_DENIED` before it reaches the tool server. IT provisioning cannot read HR salary data. The training skill cannot post to Slack. The manager handoff skill cannot create employee records.

This is the confused deputy problem solved at the architectural level — not through prompting, but through deterministic code.

### Intelligent Model Routing (Day 3)

The system routes different skills to different model tiers:

- **HR, IT, Manager** → `gemini-2.0-flash` — fast, structured JSON output
- **Training curriculum** → `gemini-2.5-flash` — more capable model for complex reasoning (building a personalized 30-60-90 day plan and matching role-specific courses)

This is the token economy principle from Day 3: don't use an expensive frontier model for tasks that a smaller model handles perfectly.

### Evaluation-Driven Development (Day 5)

Each skill has 3 JSON evaluation cases written before the skill instructions were finalized. The trajectory scorer validates the **sequence** of tool calls, not just the final output — the core insight from Day 5 that output-only scoring passes 20–50% more cases than it should.

The scorer applies the **Pass-to-K metric** (p^k): a skill must succeed on k consecutive runs to be promoted to production. The current system achieves 91% pass rate across 11 evaluated cases, with Pass-to-K(5) = 62% — above the production threshold.

### Spec-Driven Development (Day 5)

Every skill's behavior is fully specified in `skill.md` before any code runs. The `skill.md` files are the single source of truth — not the orchestrator code, not the prompts. When requirements change (e.g., a new document type for contractors), only the `skill.md` changes. The orchestrator code is untouched. Code became disposable; the spec became permanent.

---

## Results

Running `python3 kaggle_demo.py --mock` produces:

| Metric | Value |
|---|---|
| Steps completed | 4 / 4 |
| Total tool calls | 28 |
| Employee ID generated | EMP-XXXXXXXX |
| Corporate email provisioned | geesh.mamidi@company.com |
| GitHub account created | @geesh-mamidi (member, not admin) |
| Slack channels joined | #engineering, #general, #deploys |
| Licenses assigned | GitHub Pro, VSCode, Jira |
| Training courses assigned | 8 (4 compliance + 4 role-specific) |
| Calendar events created | 8 (Day-1 check-in through 90-day review) |
| Emails sent | 3 (compliance docs, learning plan, manager briefing) |
| Slack messages posted | 2 (welcome to #engineering and #general) |
| Eval cases passed | 10 / 11 (91%) |
| Pass-to-K (k=5) | 62.1% — production ready |
| Active context budget | ~1,710 tokens (vs ~15,000 without progressive disclosure) |

---

## Business Impact

For a company that hires 10 engineers per month, this system saves an estimated 40–60 person-hours per month of manual coordination across HR, IT, and People Ops. More importantly, it eliminates the category of errors that come from human handoffs — the IT ticket that never gets filed, the training that gets skipped because no one sent the link, the manager who finds out about their new hire the morning they arrive.

The architecture is designed to scale. Adding a new department or onboarding variant means writing one `skill.md` file — no engineering required. Domain experts (HR managers, compliance officers) can write skills directly. This is the distributed ownership model from Day 3's enterprise case study: domain experts encode procedural knowledge that the AI reads on demand, rather than AI engineers having to become domain experts themselves.

---

## What I Would Build Next

With live Gemini API access and more time, the immediate next steps would be:

1. **Real MCP servers** — replace mock tools with actual Slack, GitHub, and Google Workspace MCP endpoints. The architecture already supports this; it's a one-line change per tool.
2. **A2A delegation** — for edge cases requiring human judgment (offer renegotiations, special accommodation requests), the orchestrator would delegate to a human-in-the-loop agent via the A2A protocol.
3. **Meta-skill** — a skill that watches onboarding completion rates and automatically proposes new skills when it detects recurring failure patterns in the trajectory logs.
4. **Kaggle SAE integration** — register the agent via `skill.md` to autonomously fetch exam questions and post scores, demonstrating the autonomous exam pattern from Day 4.

---

## Running the Project

```bash
git clone https://github.com/YOUR_USERNAME/onboarding-agent
cd onboarding-agent
pip install -r requirements.txt

# Run without API key (mock mode — full pipeline, no LLM calls)
python3 kaggle_demo.py --mock

# Run with Gemini API (live mode)
export GEMINI_API_KEY="your_key"
python3 kaggle_demo.py
```

Open `dashboard/dashboard.html` in a browser to see the A2UI live onboarding dashboard.

---

## Conclusion

This project is a direct implementation of the agentic engineering paradigm taught in the course — the opposite of vibe coding. Every component has a reason rooted in a specific course concept: the DAG from the factory model, the skills from progressive disclosure, the MCP gateway from zero ambient authority, the trajectory scorer from evaluation-driven development.

The result is a system that is not just functional but maintainable, auditable, and extensible — the properties that separate a production agent from a demo.

---

*Word count: ~1,480 words*
