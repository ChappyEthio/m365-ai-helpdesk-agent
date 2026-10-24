# ALM: dev → test → prod

| Environment | Solution type | Who changes it |
|---|---|---|
| DEV | Unmanaged | Makers and developers |
| TEST | Managed | Pipeline only |
| PROD | Managed | Pipeline only, after reviewer approval |

**Flow of a change:** build in DEV → run *export-from-dev* → review the pull request (diff of the unpacked solution) → merge → pipeline packs a managed solution, runs the solution checker, deploys to TEST with `deployment-settings/test.json` → reviewer approves → deploys to PROD with `deployment-settings/prod.json`.

**Dependencies:** the solution contains the agent, topics, flows, the custom connector, connection references and environment variables. Standard connectors (Approvals, Office 365 Users, Teams) exist in every environment; the custom connector travels inside the solution.

**Connection references** bind each flow to an environment's connection at import time, so no flow is edited after deployment. **Environment variables** hold values that differ per environment (alert channel, API URL).
