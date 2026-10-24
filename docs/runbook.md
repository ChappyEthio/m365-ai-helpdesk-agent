# Runbook

## Daily / on alert

| Signal | Where | Action |
|---|---|---|
| "Helpdesk agent flow failed" in IT alerts channel | Teams | Open the run link → read the failed action → fix cause → **Resubmit** the run. Safe to resubmit: ticket creation is idempotent (run ID key). |
| User reports "the bot didn't answer" | Copilot Studio → Analytics → Sessions | Check whether it was a refusal (no approved content) or an error; add a KB article or fix the topic |
| API errors / latency | Application Insights → Failures, Performance | Check recent deployments; scale the App Service plan if CPU-bound |

## Weekly

- Run `admin/Test-PlatformHealth.ps1`; renew any credential within 30 days of expiry (certificate preferred).
- Review approvals older than 2 days that timed out and contact the requester.

## Monthly

- `admin/Get-M365LicenseReport.ps1`: reclaim licences from users inactive 45+ days (after HR check).
- Review unanswered questions and add the top 5 to the knowledge base and to `evaluation/dataset.jsonl`.
- Run `python -m evaluation.run_eval --generator azure` against the production model and compare with last month.

## Recovery

| Failure | Recovery |
|---|---|
| Ticket API down | Flow retries 4 times, then alerts IT; user gets a reference. After recovery, resubmit failed runs from the alert links. |
| Connector key rotated | Update the secret in Key Vault; edit the connection in each environment (connection references keep flows unchanged). |
| Bad release in PROD | Re-run the ALM pipeline on the previous `main` commit; the earlier managed solution version is re-imported. |
