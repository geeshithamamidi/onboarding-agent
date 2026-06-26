# 5-Minute Video Script
## Smart Employee Onboarding Orchestrator — Kaggle Capstone Demo

**Total time: 5:00** | Record your screen + terminal + browser

---

### [0:00 – 0:30] Hook & Problem (30 sec)

**Show:** Slide or blank screen with text, or just talk to camera.

**Say:**
> "Every company onboards new employees the same way — HR sends emails manually,
> IT creates accounts one by one, someone forgets to assign training, and the manager
> finds out about their new hire the morning they walk in.
>
> What if an AI agent could handle all of that — automatically, in seconds, with full
> audit trails and zero human handoffs?
>
> That's what I built for this capstone."

---

### [0:30 – 1:00] Architecture Overview (30 sec)

**Show:** Open `dashboard/dashboard.html` in browser — the A2UI dashboard.

**Say:**
> "This is the Smart Employee Onboarding Orchestrator. It's built on every concept
> from the 5-day course — agent skills, MCP, DAG orchestration, zero ambient authority,
> and evaluation-driven development.
>
> The pipeline has 4 steps: HR intake, IT provisioning, training assignment, and manager
> handoff. Each step is a specialist skill — not a separate agent, but a skill.md file
> that gets loaded on demand. That's progressive disclosure from Day 3."

**Point to the pipeline diagram in the dashboard.**

---

### [1:00 – 1:30] The Skill Files (30 sec)

**Show:** Open VS Code or terminal, show `.agent-skills/hr/skill.md`.

**Say:**
> "Here's the HR skill. This markdown file IS the spec — a Day 5 concept called
> spec-driven development. It defines exactly what tools HR is allowed to call,
> what steps to follow, and what the output schema must look like.
>
> Notice the guardrails section — compensation data is never passed to any other skill.
> That's zero ambient authority from Day 4.
>
> The IT skill, the training skill, and the manager skill each have their own file.
> Adding a new department means writing one new file — no new agents, no new deployments."

---

### [1:30 – 3:00] Live Demo — Run the Pipeline (90 sec)

**Show:** Terminal. Run `python3 kaggle_demo.py --mock`

**Say as it runs:**
> "Let me run it. I'm using mock mode today — all the real MCP tools execute,
> but the LLM decisions are scripted so it works without API quota limits."

*[HR step runs — 3 tool calls appear]*
> "Step 1 — HR intake. Watch the tool calls: first it validates the department,
> then creates the employee record, then sends the compliance document packet.
> That's the correct trajectory — the order matters, and the evaluator checks it."

*[IT step runs — 4 tool calls]*
> "Step 2 — IT provisioning. Corporate email, GitHub with member-level access — not admin,
> never admin — Slack channels matched to the role, and software licenses. 
> This skill can't see the salary data from HR. The MCP gateway blocks it."

*[Training step runs — 12 tool calls]*
> "Step 3 — Training. Eight courses assigned: four mandatory compliance courses that
> every employee gets, plus four engineering-specific courses. Calendar sessions scheduled.
> Learning plan emailed to the corporate address."

*[Manager step runs — 8 tool calls]*
> "Step 4 — Manager handoff. Five calendar events from Day 1 check-in through the
> 90-day review. And here — the Slack welcome message. This goes to the engineering
> channel and general. Notice it's warm and personal, not a system log line."

*[Pipeline complete — summary prints]*
> "28 tool calls. 4 steps. All complete."

---

### [3:00 – 3:45] Evaluation Results (45 sec)

**Show:** Terminal — the evaluation output. Or `evals/eval_report.json`.

**Say:**
> "Now here's the part that separates agentic engineering from vibe coding — evaluation.
>
> The trajectory scorer checks the sequence of tool calls, not just the final output.
> Day 5 taught us that output-only scoring passes 20 to 50 percent more test cases
> than it should — because the agent might reach the right answer through a dangerous path.
>
> 10 out of 11 cases pass. 91% pass rate. Pass-to-K with k equals 5 is 62 percent —
> above the production threshold of 50 percent.
>
> And notice: active context is 1,710 tokens versus 15,000 if we loaded everything upfront.
> Progressive disclosure cut context by 88 percent."

---

### [3:45 – 4:30] Key Concepts Callout (45 sec)

**Show:** `message_bus/` folder — show the 6 JSON files written by the pipeline.

**Say:**
> "A few things I want to highlight.
>
> The file message bus — each skill writes its output to a JSON file here and the next
> skill reads from it. Skills never dump large outputs back into the context window.
> That's how we prevent context rot.
>
> The MCP tool registry — every tool has a standard schema and a dispatch method.
> Swapping a mock tool for a real Slack MCP server is one line of code. That's the
> NxM to N-plus-M complexity reduction from Day 2.
>
> And the trajectory log — every single tool call is recorded with its parameters
> and result. Full observability. If something goes wrong in production, you can
> replay exactly what happened."

---

### [4:30 – 5:00] Closing (30 sec)

**Show:** Browser — the A2UI dashboard animating.

**Say:**
> "What I built here is a direct implementation of the factory model from Day 3.
> I'm not the worker laying every brick — I'm the engineer on the catwalk, designing
> the robotic arms and the quality control sensors.
>
> The agent does the work. My job is to make sure the harness is right.
>
> The code is on GitHub — link in the writeup. You can run it yourself in 30 seconds
> with a single command. Thanks for watching."

---

## Recording Tips

- **Screen record** using QuickTime (Mac): File → New Screen Recording
- **Terminal font size**: increase to 16pt so text is readable on video
- **Run the pipeline once before recording** so you know the timing
- **Upload to YouTube**: set visibility to "Unlisted" (not private — judges need the link)
- **Thumbnail**: screenshot of the A2UI dashboard

## What to Show in Order
1. Dashboard in browser (pipeline diagram)
2. `skill.md` file in VS Code or `cat .agent-skills/hr/skill.md` in terminal
3. `python3 kaggle_demo.py --mock` running live
4. Eval output at the bottom
5. `message_bus/` folder files
6. Dashboard again for closing shot
