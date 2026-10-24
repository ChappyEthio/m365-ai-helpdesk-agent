# Agent configuration (Copilot Studio)

**Name:** IT Helpdesk Assistant
**Channels:** Microsoft Teams, Microsoft 365 Copilot (as an agent)
**Authentication:** Microsoft Entra ID (users sign in; the agent acts with the user's identity, so SharePoint permissions are enforced)

## Instructions (generative orchestration)

You are the IT helpdesk assistant for staff.
- Answer only from the connected knowledge sources and cite the article you used.
- If the knowledge sources do not answer the question, say so and offer to create a ticket. Never guess steps, links or policies.
- Never ask for, repeat or store passwords, MFA codes or recovery keys.
- Requests that change access or security (mailbox access, MFA reset, admin rights) always go through the Create IT ticket topic, which requires manager approval.
- Keep answers short and practical. Use numbered steps for procedures.

## Knowledge sources

| Source | Who can see it | Notes |
|---|---|---|
| SharePoint site `IT Knowledge Base` (all-staff library) | All staff | Mirrors `knowledge/kb-00x` |
| SharePoint library `IT Admin Runbooks` | `IT Admins` security group only | Mirrors `knowledge/kb-900`; trimmed for everyone else |

Because the agent uses the signed-in user's identity, SharePoint security trimming decides what each person
can get answers from. The evaluation harness tests the same rule offline (cases Q07 and Q08).

## Actions

| Action | Type | Purpose |
|---|---|---|
| Create IT ticket | Power Automate flow `CreateTicketWithApproval` | Ticket with validation, retry and manager approval |
| Ticket status | Custom connector `GetTicket` | "What's the status of HD-1234?" |

## Foundry option

For questions that need more control (custom retrieval, model choice, cost limits), the same knowledge can be
served by a Microsoft Foundry agent behind Azure API Management, added to Copilot Studio as an action.
`evaluation/generators.py` (`AzureOpenAIGenerator`) shows the grounded prompt and how answers are scored.
