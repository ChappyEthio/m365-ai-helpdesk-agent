<#
.SYNOPSIS
  Weekly platform health check: app registration credentials close to expiry
  (a common cause of silent flow and connector failures) and app registrations
  with high-privilege Graph permissions that need review.
.EXAMPLE
  ./Test-PlatformHealth.ps1 -WarnDays 30
#>
param([int] $WarnDays = 30)
$ErrorActionPreference = "Stop"
Import-Module Microsoft.Graph.Applications
Connect-MgGraph -Scopes "Application.Read.All" -NoWelcome

$now = Get-Date
$creds = foreach ($app in Get-MgApplication -All -Property "id,appId,displayName,passwordCredentials,keyCredentials") {
    foreach ($c in $app.PasswordCredentials) { [pscustomobject]@{ App = $app.DisplayName; AppId = $app.AppId; Type = "Secret"; End = $c.EndDateTime } }
    foreach ($c in $app.KeyCredentials)      { [pscustomobject]@{ App = $app.DisplayName; AppId = $app.AppId; Type = "Certificate"; End = $c.EndDateTime } }
}
$findings = foreach ($c in $creds | Where-Object End) {
    $days = [int]($c.End - $now).TotalDays
    if ($days -le $WarnDays) {
        [pscustomobject]@{
            App      = $c.App
            AppId    = $c.AppId
            Type     = $c.Type
            Expires  = $c.End
            DaysLeft = $days
            Status   = if ($days -lt 0) { "EXPIRED" } elseif ($days -le 7) { "CRITICAL" } else { "WARNING" }
        }
    }
}

$risky = "Directory.ReadWrite.All", "Sites.FullControl.All", "Mail.ReadWrite", "RoleManagement.ReadWrite.Directory"
$graph = Get-MgServicePrincipal -Filter "appId eq '00000003-0000-0000-c000-000000000000'"
$roleNames = @{}; $graph.AppRoles | ForEach-Object { $roleNames[$_.Id] = $_.Value }
$privileged = foreach ($sp in Get-MgServicePrincipal -All -Filter "servicePrincipalType eq 'Application'") {
    $granted = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id |
        Where-Object ResourceId -eq $graph.Id | ForEach-Object { $roleNames[$_.AppRoleId] }
    $hit = $granted | Where-Object { $_ -in $risky }
    if ($hit) { [pscustomobject]@{ App = $sp.DisplayName; HighPrivilegePermissions = ($hit -join ", ") } }
}

"`n== Credentials expiring within $WarnDays days =="; $findings | Sort-Object DaysLeft | Format-Table -AutoSize
"`n== Apps with high-privilege Graph permissions (review) =="; $privileged | Format-Table -AutoSize
if ($findings | Where-Object Status -in "EXPIRED", "CRITICAL") { exit 1 }
