---
name: it-provisioning
description: >
  Activate after HR intake is complete (hr_output.json exists in message_bus).
  This skill provisions all technical access for a new employee: creates their corporate
  email account, adds them to relevant GitHub teams, creates their Slack workspace account,
  and sets up software licenses. Uses only the employee_id and role from HR output —
  never accesses HR salary or personal data. Trigger: "provision accounts", "setup IT access",
  "create accounts for new hire".
metadata:
  type: skill
  department: IT
  security_tier: standard
  allowed_tools: [it_create_email, it_provision_github, it_provision_slack, it_assign_licenses]
  forbidden_data: [compensation, tax_documents, personal_email, benefits]
---

# IT Provisioning Skill

## Purpose
Provision all digital infrastructure for a new employee based on their role.

## Input Schema (read from message_bus/hr_output.json)
```json
{
  "employee_id": "string",
  "full_name": "string",
  "role": "string",
  "department": "string",
  "start_date": "YYYY-MM-DD"
}
```
Only these 5 fields are permitted. Do NOT read `compensation`, `personal_email`,
or any document fields from the HR output.

## Role-to-Access Mapping
Use this mapping to determine what to provision:

| Role keyword    | GitHub teams          | Slack channels                    | Licenses               |
|-----------------|-----------------------|-----------------------------------|------------------------|
| engineer/dev    | eng-general, product  | #engineering, #general, #deploys  | GitHub Pro, VSCode, Jira |
| designer        | design                | #design, #general, #brand         | Figma, Notion, Jira    |
| manager/lead    | leadership, eng-general | #leadership, #general, #deploys | GitHub Pro, Jira, Notion|
| analyst/data    | data-team             | #data, #general, #analytics       | Looker, Notion, Jira   |
| default         | general-staff         | #general, #announcements          | Notion, Jira           |

## Steps

1. **Read HR output** — Load `message_bus/hr_output.json`. Extract only the 5
   permitted fields. Confirm `status` is "success" before proceeding.

2. **Generate corporate email** — Format: `firstname.lastname@company.com`
   (lowercase, dots between first and last name).
   Call `it_create_email(employee_id, corporate_email)`.

3. **Determine access profile** — Match `role` against the mapping table above.
   Default to "default" tier if no keyword matches.

4. **Provision GitHub** — Call `it_provision_github(employee_id, teams)` with the
   matched team list. Store returned `github_username`.

5. **Provision Slack** — Call `it_provision_slack(employee_id, corporate_email, channels)`.
   Store returned `slack_id`.

6. **Assign licenses** — Call `it_assign_licenses(employee_id, license_list)`.

7. **Write output** — Save to `message_bus/it_output.json`.

## Output Schema
```json
{
  "skill": "it-provisioning",
  "status": "success | failed",
  "employee_id": "string",
  "corporate_email": "string",
  "github_username": "string",
  "slack_id": "string",
  "github_teams": ["list"],
  "slack_channels": ["list"],
  "licenses_assigned": ["list"],
  "error": "null | string"
}
```

## Guardrails
- NEVER read or log HR compensation, personal email, or tax document fields.
- NEVER grant admin/owner permissions — all provisioning is at member level only.
- If `it_create_email` returns a conflict (email already exists), generate a
  numeric suffix variant (e.g., firstname.lastname2@company.com) and retry once.
- If any provisioning step fails, still attempt remaining steps and report partial
  success with a list of failed steps in the error field.
