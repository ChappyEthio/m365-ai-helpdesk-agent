# Security model

| Area | Control |
|---|---|
| Identity | Users sign in with Entra ID; the agent answers as the user, so SharePoint permissions apply |
| App permissions | One app registration, Graph `Sites.Selected` with **read on one site**; certificate credential (`admin/New-HelpdeskAgentAppRegistration.ps1`) |
| Secrets | API key in Key Vault; App Service reads it through a managed identity with the *Key Vault Secrets User* role on that vault only; makers never see it |
| Consequential actions | Manager approval for access/security changes, enforced in flow **and** API |
| Data minimisation | The agent never asks for or stores passwords, MFA codes or recovery keys (agent instructions) |
| Deployment | Service principal per pipeline, least-privilege security role in each environment; prod requires a reviewer |
| Monitoring | Application Insights for the API; Teams alerts for flow failures; weekly credential and privilege review |
| Data protection law | Designed for data-protection laws such as Ethiopia's Personal Data Protection Proclamation No. 1321/2024: purpose-limited data, least privilege, audit trail on tickets |
