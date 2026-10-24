// Azure resources for the ticket API: hosting, secrets and monitoring.
// Deploy:  az deployment group create -g rg-helpdesk-agent-dev -f infra/main.bicep -p env=dev

@allowed(['dev', 'test', 'prod'])
param env string = 'dev'
param location string = resourceGroup().location
param appName string = 'helpdesk-api'

var suffix = '${appName}-${env}'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${suffix}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${suffix}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take('kv-${replace(suffix, '-', '')}${uniqueString(resourceGroup().id)}', 24)
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
    enablePurgeProtection: true
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'asp-${suffix}'
  location: location
  sku: { name: env == 'prod' ? 'B2' : 'B1' }
  kind: 'linux'
  properties: { reserved: true }
}

resource site 'Microsoft.Web/sites@2023-12-01' = {
  name: suffix
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appCommandLine: 'uvicorn src.ticket_api.main:app --host 0.0.0.0 --port 8000'
      appSettings: [
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
        { name: 'WEBSITES_PORT', value: '8000' }
        // The API key is read from Key Vault at runtime; it never appears in config or code.
        { name: 'HELPDESK_API_KEY', value: '@Microsoft.KeyVault(VaultName=${vault.name};SecretName=helpdesk-api-key)' }
      ]
    }
  }
}

// Key Vault Secrets User, scoped to this vault only, for the web app's managed identity
var kvSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
resource secretsAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, site.id, kvSecretsUser)
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUser)
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output apiUrl string = 'https://${site.properties.defaultHostName}'
output keyVaultName string = vault.name
