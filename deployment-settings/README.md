# Deployment settings

One file per target environment, in the format produced by `pac solution create-settings`.
They hold environment variable values and the connection to bind to each connection reference,
so the same managed solution deploys to test and prod without editing flows.

Connection IDs are not secrets, but they are environment-specific: fill them in after creating
the connections (owned by the deployment service account) in each environment.
