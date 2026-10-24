# Project plan: from requirement to production

How this project would be run with a small team, including outsourced developers.

## Business requirement

> Staff lose time waiting for IT with simple questions, and access requests are approved informally by chat.
> We want an assistant in Teams that answers common IT questions from approved guidance and creates tickets,
> with manager approval for anything that changes access or security.

## User stories and acceptance criteria

| # | Story | Acceptance criteria |
|---|---|---|
| US1 | As staff, I ask an IT question in Teams and get an answer from approved guidance | Answer cites a KB article; citation accuracy >= 80% on the evaluation set; no answer for out-of-scope questions |
| US2 | As staff, I only get answers from content I am allowed to see | 0 permission leaks in evaluation (restricted article never returned to non-admins) |
| US3 | As staff, I can create a ticket from the chat | Ticket created with category, title, description; user gets ticket ID in the chat |
| US4 | As a manager, I approve access/security requests before IT acts | High-risk ticket stays `PendingApproval` until approved; approval ID recorded; API rejects opening without it |
| US5 | As IT, I know immediately when automation fails | Failure posts to the IT Teams channel with error and run link within 1 minute; user receives a reference |
| US6 | As the platform owner, I deploy changes safely | Changes reach prod only from `main`, as a managed solution, after tests, evaluation gate and an approver |

## Milestones

| Milestone | Scope | Exit criteria |
|---|---|---|
| M1 Foundations (week 1) | Environments, app registration, ALM pipeline, ticket API skeleton | Pipeline exports from DEV and deploys an empty solution to TEST |
| M2 Answers (week 2) | Knowledge sources, agent instructions, evaluation set v1 | US1 and US2 pass the evaluation gate |
| M3 Tickets and approvals (week 3) | Connector, flow, approval, alerts | US3–US5 demonstrated in TEST |
| M4 Pilot (week 4) | One department, feedback, tuning | 2 weeks of pilot data; evaluation set extended with real questions |
| M5 Production | Rollout, runbook handover | US6 complete; runbook signed off |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agent gives a confident wrong answer | Medium | High | Grounding only on approved KB; refusal path; evaluation gate in CI; monthly review of unanswered questions |
| Restricted content exposed | Low | High | Agent uses user identity; restricted library; leak test cases (Q07) block deployment |
| Approval bypassed | Low | High | Server-side rule in the API as well as the flow |
| Licence or consumption costs grow | Medium | Medium | Monthly licence report (`admin/Get-M365LicenseReport.ps1`); evaluation reports cost per question |
| Expired credential silently breaks flows | Medium | Medium | Weekly `Test-PlatformHealth.ps1`; certificates over secrets |
| Outsourced work drifts from standards | Medium | Medium | PR template, required review, solution checker, tests in CI |

## Working with outsourced developers

- **Clear tasks:** each task links to a user story and its acceptance criteria; done means demonstrated in DEV and merged.
- **Own DEV environment or branch**, never direct changes in TEST or PROD; the pipeline is the only way in.
- **Pull request review** using `.github/pull_request_template.md`: no hard-coded values, error handling present, least privilege, cost impact noted.
- **Weekly 30-minute demo** against acceptance criteria; fixed scope per sprint so the budget stays predictable.
