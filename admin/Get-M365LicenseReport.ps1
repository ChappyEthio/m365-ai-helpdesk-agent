<#
.SYNOPSIS
  Licence and spend check: unused licences per SKU and licensed users with no sign-in for N days.
.EXAMPLE
  ./Get-M365LicenseReport.ps1 -InactiveDays 45 -OutFolder ./reports
#>
param(
    [int] $InactiveDays = 45,
    [string] $OutFolder = "./reports"
)
$ErrorActionPreference = "Stop"
Import-Module Microsoft.Graph.Identity.DirectoryManagement, Microsoft.Graph.Users
Connect-MgGraph -Scopes "Organization.Read.All", "User.Read.All", "AuditLog.Read.All" -NoWelcome
New-Item -ItemType Directory -Force -Path $OutFolder | Out-Null

$skus = Get-MgSubscribedSku | ForEach-Object {
    [pscustomobject]@{
        Sku       = $_.SkuPartNumber
        Purchased = $_.PrepaidUnits.Enabled
        Assigned  = $_.ConsumedUnits
        Unused    = $_.PrepaidUnits.Enabled - $_.ConsumedUnits
    }
}
$skus | Sort-Object Unused -Descending | Export-Csv "$OutFolder/licence-summary.csv" -NoTypeInformation

$cutoff = (Get-Date).AddDays(-$InactiveDays)
$inactive = Get-MgUser -All -Property "displayName,userPrincipalName,assignedLicenses,signInActivity,accountEnabled" |
    Where-Object { $_.AssignedLicenses.Count -gt 0 } |
    Where-Object { -not $_.SignInActivity.LastSignInDateTime -or $_.SignInActivity.LastSignInDateTime -lt $cutoff } |
    Select-Object DisplayName, UserPrincipalName, AccountEnabled,
        @{ n = "LastSignIn"; e = { $_.SignInActivity.LastSignInDateTime } },
        @{ n = "Licences"; e = { $_.AssignedLicenses.Count } }
$inactive | Export-Csv "$OutFolder/inactive-licensed-users.csv" -NoTypeInformation

Write-Host ("SKUs: {0}  |  Unused licences: {1}  |  Licensed users inactive {2}+ days: {3}" -f `
    $skus.Count, ($skus | Measure-Object Unused -Sum).Sum, $InactiveDays, $inactive.Count)
