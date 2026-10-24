<#
.SYNOPSIS
  Creates the Entra ID app registration used by the helpdesk agent's backend and the ALM pipeline,
  with least-privilege access: read-only to ONE SharePoint site via Sites.Selected.

.DESCRIPTION
  - Grants the Microsoft Graph application permission Sites.Selected (no tenant-wide site access).
  - Gives the app 'read' on the IT Knowledge Base site only.
  - Uses a certificate credential. No client secret is created here; if a secret is unavoidable,
    create it with a 6-month expiry and store it in Azure Key Vault.

.EXAMPLE
  ./New-HelpdeskAgentAppRegistration.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/ITKnowledgeBase" -CertificatePath ./agent.cer
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string] $SiteUrl,
    [Parameter(Mandatory)] [string] $CertificatePath,
    [string] $DisplayName = "sp-helpdesk-agent"
)

$ErrorActionPreference = "Stop"
Import-Module Microsoft.Graph.Applications, Microsoft.Graph.Sites

Connect-MgGraph -Scopes "Application.ReadWrite.All", "AppRoleAssignment.ReadWrite.All", "Sites.FullControl.All" -NoWelcome

# 1. App registration with a certificate credential
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath)
$app = Get-MgApplication -Filter "displayName eq '$DisplayName'"
if (-not $app) {
    if ($PSCmdlet.ShouldProcess($DisplayName, "Create app registration")) {
        $app = New-MgApplication -DisplayName $DisplayName -SignInAudience "AzureADMyOrg" -KeyCredentials @(@{
            Type = "AsymmetricX509Cert"; Usage = "Verify"; Key = $cert.RawData; DisplayName = "agent-cert"
        })
    }
}
$sp = Get-MgServicePrincipal -Filter "appId eq '$($app.AppId)'"
if (-not $sp) { $sp = New-MgServicePrincipal -AppId $app.AppId }

# 2. Grant Graph application permission Sites.Selected (looked up by value, not a hard-coded GUID)
$graph = Get-MgServicePrincipal -Filter "appId eq '00000003-0000-0000-c000-000000000000'"
$role = $graph.AppRoles | Where-Object { $_.Value -eq "Sites.Selected" -and $_.AllowedMemberTypes -contains "Application" }
$existing = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id | Where-Object AppRoleId -eq $role.Id
if (-not $existing -and $PSCmdlet.ShouldProcess("Sites.Selected", "Grant to $DisplayName")) {
    New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id -PrincipalId $sp.Id -ResourceId $graph.Id -AppRoleId $role.Id | Out-Null
}

# 3. Read access to exactly one site
$uri = [Uri]$SiteUrl
$site = Get-MgSite -SiteId "$($uri.Host):$($uri.AbsolutePath)"
$body = @{
    roles = @("read")
    grantedToIdentities = @(@{ application = @{ id = $app.AppId; displayName = $DisplayName } })
}
if ($PSCmdlet.ShouldProcess($SiteUrl, "Grant read to $DisplayName")) {
    New-MgSitePermission -SiteId $site.Id -BodyParameter $body | Out-Null
}

[pscustomobject]@{
    DisplayName = $DisplayName
    AppId       = $app.AppId
    TenantId    = (Get-MgContext).TenantId
    Permission  = "Graph Sites.Selected (read on $SiteUrl only)"
    Credential  = "Certificate thumbprint $($cert.Thumbprint)"
}
