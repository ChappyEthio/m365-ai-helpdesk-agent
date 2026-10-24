# Unpacked solutions

`HelpdeskAgent/` is created here by the **export-from-dev** job in `.github/workflows/power-platform-alm.yml`
(`pac solution unpack`). It holds the agent, topics, flows, connector and connection references as
reviewable source files. Do not edit it by hand: change things in DEV, export, review the pull request, merge.

Rules this repo follows:
- **Unmanaged in DEV, managed everywhere else.** Test and prod only ever receive a managed solution packed from `main`.
- **Connection references and environment variables**, never hard-coded connections or URLs.
- **One publisher prefix (`cr_`)** for every component, so ownership and dependencies stay clear.
