# Helpdesk Ticketing custom connector

OpenAPI 2.0 definition for the ticket API in `src/ticket_api`, in the format used by the
Power Platform connector CLI (`paconn`) and the custom connector wizard.

- **Auth:** API key in the `x-api-key` header. The key is stored in Azure Key Vault and entered once per environment when the connection is created; makers never see it.
- **Idempotency:** `CreateTicket` takes an `Idempotency-Key` header. The flow passes its run ID, so a retried call returns the same ticket instead of a duplicate.
- **Environments:** change `host` per environment, or use a policy template to set it from an environment variable.

```bash
pip install paconn
paconn login
paconn create --api-def apiDefinition.swagger.json --api-prop apiProperties.json --environment <ENV_ID>
```

After creation, add the connector to the `HelpdeskAgent` solution so it travels with the ALM pipeline.
