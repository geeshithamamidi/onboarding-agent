---
name: hr-intake
description: >
  Activate when a new hire onboarding is initiated. This skill collects and validates
  new employee personal information, creates their official HR record in the HRIS system,
  generates required compliance documents (offer acknowledgement, tax forms, NDAs),
  and confirms the employee's start date. Trigger phrase: "new hire", "onboard employee",
  "start onboarding for".
metadata:
  type: skill
  department: HR
  security_tier: restricted
  allowed_tools: [hris_create_employee, hris_get_departments, email_send_document]
  forbidden_data: [it_logs, training_records, manager_notes]
---

# HR Intake Skill

## Purpose
Create the official HR record and dispatch all Day-1 compliance paperwork for a new hire.

## Input Schema
```json
{
  "full_name": "string",
  "email": "string (personal, pre-corporate)",
  "role": "string",
  "department": "string",
  "start_date": "YYYY-MM-DD",
  "employment_type": "full_time | part_time | contractor",
  "manager_name": "string",
  "compensation": "number (DO NOT pass to any other skill)"
}
```

## Steps

1. **Validate input** — Check all required fields are present and non-empty.
   If `start_date` is in the past, halt and return error `INVALID_START_DATE`.

2. **Verify department** — Call `hris_get_departments()` to confirm `department`
   is a valid org unit. If not found, halt with error `INVALID_DEPARTMENT`.

3. **Create employee record** — Call `hris_create_employee()` with all input fields.
   Store the returned `employee_id` — it is required by all downstream skills.
   Never log the `compensation` field.

4. **Generate compliance documents** — Using the employee record, list the required
   documents based on `employment_type`:
   - full_time: offer_acknowledgement, tax_w4, nda, benefits_enrollment
   - contractor: contractor_agreement, tax_w9, nda
   - part_time: offer_acknowledgement, tax_w4, nda

5. **Send document packet** — Call `email_send_document()` with:
   - recipient: input `email`
   - subject: "Welcome to [Company] — Action Required: Day-1 Documents"
   - documents: list from step 4
   - deadline: 2 business days before `start_date`

6. **Write output** — Save result to `message_bus/hr_output.json` using this schema:

## Output Schema
```json
{
  "skill": "hr-intake",
  "status": "success | failed",
  "employee_id": "string",
  "full_name": "string",
  "role": "string",
  "department": "string",
  "start_date": "YYYY-MM-DD",
  "corporate_email": "string (to be provisioned by IT)",
  "documents_sent": ["list of document names"],
  "documents_deadline": "YYYY-MM-DD",
  "error": "null | string"
}
```

## Guardrails
- NEVER include `compensation` in output — redact as `[REDACTED]`.
- NEVER call IT provisioning tools from within this skill.
- If `hris_create_employee` returns a duplicate employee warning, halt with
  error `DUPLICATE_EMPLOYEE` — do not create a second record.
- Maximum 3 retries on any tool call before marking step as failed.
