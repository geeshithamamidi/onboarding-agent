---
name: manager-handoff
description: >
  Activate as the final step after training assignment is complete (training_output.json
  exists in message_bus). This skill prepares the hiring manager for their new team
  member's arrival: generates a manager briefing pack, schedules Day-1 check-ins and
  weekly 1:1s for the first 90 days, sends a welcome message to the team Slack channel,
  and produces the final onboarding completion report. Trigger: "manager handoff",
  "notify manager", "complete onboarding", "finalize onboarding".
metadata:
  type: skill
  department: People Operations
  security_tier: standard
  allowed_tools: [calendar_schedule_session, slack_post_message, email_send_document]
  forbidden_data: [compensation, tax_documents, github_credentials, slack_credentials, training_scores]
---

# Manager Handoff Skill

## Purpose
Prepare the manager and team for the new hire's arrival. Produce the final
onboarding completion report.

## Input Schema (read from all previous message_bus outputs)
```json
{
  "from_hr": {
    "employee_id": "string", "full_name": "string", "role": "string",
    "department": "string", "start_date": "YYYY-MM-DD", "manager_name": "string",
    "corporate_email": "string"
  },
  "from_it": {
    "corporate_email": "string", "slack_id": "string",
    "github_username": "string", "slack_channels": ["list"]
  },
  "from_training": {
    "courses_assigned": ["list"], "sessions_scheduled": ["list"],
    "thirty_sixty_ninety_plan": {}
  }
}
```

## Steps

1. **Read all message_bus outputs** — Load hr_output.json, it_output.json,
   training_output.json. Confirm all have status "success".

2. **Generate manager briefing** — Create a structured briefing document containing:
   - New hire profile (name, role, start date, corporate email, github username)
   - IT access summary (what was provisioned)
   - Training curriculum overview (course list, key deadlines)
   - 30-60-90 day plan from training skill
   - Suggested Day-1 agenda for the manager
   Do NOT include compensation or personal email in this document.

3. **Schedule recurring 1:1s** — Call `calendar_schedule_session()` to create:
   - Week 1: Daily 15-min check-ins (Mon–Fri, 9am)
   - Weeks 2–4: 3x per week 30-min 1:1s
   - Month 2–3: Weekly 45-min 1:1s
   Invite: manager + new hire corporate email.

4. **Schedule 30/60/90 reviews** — Call `calendar_schedule_session()` for:
   - Day 30 review (30-min)
   - Day 60 review (45-min)
   - Day 90 review (60-min, includes performance discussion)

5. **Post team welcome** — Call `slack_post_message()` to #general and the
   department channel with a warm welcome message. Include:
   - New hire's name and role
   - Start date
   - GitHub username (for engineering teams)
   - An invitation for the team to say hello
   Keep it friendly and human — not robotic.

6. **Email briefing to manager** — Call `email_send_document()` to send the
   manager briefing pack to the manager's email.
   Subject: "New Team Member Starting [start_date] — Briefing Pack: [full_name]"

7. **Write final completion report** — Save to `message_bus/onboarding_complete.json`.

## Output Schema
```json
{
  "skill": "manager-handoff",
  "status": "success | failed",
  "employee_id": "string",
  "full_name": "string",
  "onboarding_complete": true,
  "completed_at": "ISO-8601 timestamp",
  "summary": {
    "hr_record_created": true,
    "accounts_provisioned": ["list of systems"],
    "courses_assigned": 8,
    "calendar_events_created": 12,
    "manager_briefing_sent": true,
    "team_notified": true
  },
  "next_actions": [
    "string (actionable next step for the manager)",
    "string",
    "string"
  ],
  "error": "null | string"
}
```

## Guardrails
- The Slack welcome message must be reviewed for tone — it must be warm and personal,
  not a system-generated announcement.
- NEVER post compensation, personal email, or tax information to Slack.
- If the manager's calendar is unavailable for Day-1 daily check-ins, schedule
  a single Day-1 welcome lunch instead and note it in next_actions.
- This is the terminal node of the DAG — after writing onboarding_complete.json,
  the orchestrator marks the onboarding as done.
