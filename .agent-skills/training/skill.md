---
name: training-assignment
description: >
  Activate after IT provisioning is complete (it_output.json exists in message_bus).
  This skill assigns a personalized onboarding learning path to the new employee based
  on their role and department. It schedules mandatory compliance training, role-specific
  technical modules, and a 30-60-90 day development plan. Sends the learning plan to
  the employee's new corporate email. Trigger: "assign training", "create learning path",
  "setup onboarding curriculum".
metadata:
  type: skill
  department: Training & Development
  security_tier: standard
  allowed_tools: [training_assign_course, training_get_catalog, calendar_schedule_session, email_send_document]
  forbidden_data: [compensation, tax_documents, github_credentials, slack_credentials]
---

# Training Assignment Skill

## Purpose
Build and assign a personalized onboarding curriculum for the new hire.

## Input Schema (read from message_bus/hr_output.json + message_bus/it_output.json)
From HR output:
```json
{ "employee_id": "string", "full_name": "string", "role": "string",
  "department": "string", "start_date": "YYYY-MM-DD" }
```
From IT output:
```json
{ "corporate_email": "string" }
```

## Mandatory Training (All Employees)
These courses are assigned to every new hire regardless of role:
- `COMP-001`: Code of Conduct & Ethics (deadline: Day 3)
- `COMP-002`: Information Security Awareness (deadline: Day 5)
- `COMP-003`: Anti-Harassment Policy (deadline: Day 5)
- `COMP-004`: Data Privacy & GDPR Basics (deadline: Day 7)

## Role-Based Learning Paths

| Role keyword  | Courses                                          | Timeline  |
|---------------|--------------------------------------------------|-----------|
| engineer/dev  | ENG-101 (Codebase Intro), ENG-102 (CI/CD),      | Week 1-2  |
|               | ENG-103 (Code Review Standards), ENG-201 (System| Week 3-4  |
|               | Design)                                          |           |
| designer      | DES-101 (Design System), DES-102 (Figma Workflow)| Week 1-2  |
|               | DES-103 (Brand Guidelines)                       | Week 3    |
| manager/lead  | MGR-101 (Management Framework), MGR-102          | Week 1-2  |
|               | (Performance Reviews), MGR-103 (Hiring Process) | Week 3-4  |
| analyst/data  | DATA-101 (Data Stack Overview), DATA-102         | Week 1-2  |
|               | (SQL Standards), DATA-103 (Dashboard Creation)  | Week 3    |
| default       | GEN-101 (Company Overview), GEN-102 (Tools Tour)| Week 1    |

## Steps

1. **Read inputs** — Load HR and IT outputs from message_bus. Validate both have
   status "success". Extract only permitted fields.

2. **Fetch catalog** — Call `training_get_catalog()` to get current course list
   and confirm all course IDs above are still active.

3. **Build curriculum** — Combine mandatory courses + role-matched path.
   Calculate deadlines relative to `start_date`.

4. **Assign courses** — Call `training_assign_course(employee_id, course_id, deadline)`
   for each course in the curriculum. Collect assignment confirmations.

5. **Schedule live sessions** — Call `calendar_schedule_session()` for:
   - Day 1: Company welcome session (all-hands intro)
   - Week 1 Day 3: 1:1 with manager (use manager from HR output via orchestrator)
   - Week 2: Role-specific technical deep-dive

6. **Send learning plan** — Call `email_send_document()` to send the full
   curriculum plan to `corporate_email` with subject:
   "Your Onboarding Learning Path — [Full Name]"

7. **Write output** — Save to `message_bus/training_output.json`.

## Output Schema
```json
{
  "skill": "training-assignment",
  "status": "success | failed",
  "employee_id": "string",
  "courses_assigned": [
    {"course_id": "string", "title": "string", "deadline": "YYYY-MM-DD"}
  ],
  "sessions_scheduled": [
    {"title": "string", "date": "YYYY-MM-DD", "duration_mins": 60}
  ],
  "plan_email_sent": true,
  "thirty_sixty_ninety_plan": {
    "day_30": "string (goal summary)",
    "day_60": "string (goal summary)",
    "day_90": "string (goal summary)"
  },
  "error": "null | string"
}
```

## Guardrails
- Never access GitHub credentials, Slack tokens, or compensation data.
- If a course ID is not found in the catalog, skip it and log in error field —
  do not halt the entire skill.
- The 30-60-90 plan must be role-specific and actionable, not generic filler.
  Generate it based on the actual role and department.
