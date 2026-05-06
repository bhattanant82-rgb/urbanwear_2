$ErrorActionPreference='Stop'
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$tokenPath = Join-Path $PSScriptRoot '..\urbanwear-backend\temp_token.txt'
if (-not (Test-Path $tokenPath)) {
    Write-Output "Temp token not found at $tokenPath";
    exit 1
}
$token = Get-Content -Raw $tokenPath

# Set admin session via helper
try {
    $h = @{ token = $token }
    $r = Invoke-RestMethod -Uri 'http://localhost/clothing_project/admin-dev-helper.php' -Method POST -Body $h -WebSession $session -UseBasicParsing
    Write-Output "Helper response: success=$($r.success) message=$($r.message)"
} catch {
    Write-Output "Helper call failed: $_"; exit 1
}

# Add 10 products via PHP proxy
for ($i=1; $i -le 10; $i++) {
    $title = "UI Product $i"
    $body = @{ action='add_product'; title=$title; price='9.99'; stock='10'; category='men'; description='Added via UI test' }
    try {
        $res = Invoke-RestMethod -Uri 'http://localhost/clothing_project/admin-api.php' -Method POST -Body $body -WebSession $session -UseBasicParsing
        Write-Output ("Add {0}: success={1} message={2}" -f $i, $res.success, $res.message)
    } catch {
        Write-Output ("Add {0}: request failed: {1}" -f $i, $_)
    }
}

# Fetch dashboard and check products
try {
    $dashboard = Invoke-WebRequest -Uri 'http://localhost/clothing_project/admin-dashboard.php' -WebSession $session -UseBasicParsing
    $content = $dashboard.Content
    $occ = [regex]::Matches($content, 'UI Product').Count
    Write-Output "Found UI product occurrences in dashboard HTML: $occ"

    if ($content -match 'Total Products[\s\S]{0,160}?<div class="value">\s*([^<]+)') {
        $val = $matches[1].Trim()
        Write-Output "Total Products value (extracted): $val"
    } else {
        Write-Output "Unable to extract Total Products value from HTML"
    }
} catch {
    Write-Output "Failed to fetch dashboard: $_"
}

# Remove helper (cleanup)
$helper = Join-Path $PSScriptRoot '..\admin-dev-helper.php'
if (Test-Path $helper) { Remove-Item $helper -Force; Write-Output 'admin-dev-helper.php removed'; } else { Write-Output 'admin-dev-helper.php not found' }
