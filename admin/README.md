# Admin scripts (Microsoft Graph PowerShell)

| Script | Purpose | Run |
|---|---|---|
| `New-HelpdeskAgentAppRegistration.ps1` | App registration with **certificate** credential and **Sites.Selected** (read on one site only) | Once per tenant, by a Global/Application admin |
| `Get-M365LicenseReport.ps1` | Unused licences per SKU and licensed users inactive for N days | Monthly, before licence renewal |
| `Test-PlatformHealth.ps1` | Credentials expiring soon (silent cause of broken flows/connectors) and apps with high-privilege Graph permissions | Weekly; exits 1 on expired/critical so it can run in a scheduled pipeline |

Requires `Install-Module Microsoft.Graph -Scope CurrentUser`. All scripts support `-WhatIf` where they change something.
