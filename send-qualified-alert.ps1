param(
    [Parameter(Mandatory=$true)][string]$JsonReport,
    [Parameter(Mandatory=$true)][string]$RunDirectory,
    [string]$Recipient = 'andriygarasivka@gmail.com'
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$statusPath = Join-Path $RunDirectory 'notification-status.json'
$statePath = Join-Path $taskRoot 'alert-state.json'
$data = Get-Content -LiteralPath $JsonReport -Raw -Encoding UTF8 | ConvertFrom-Json
$qualified = @($data.listings | Where-Object { $_.qualified_all_criteria -eq $true })

if ($qualified.Count -eq 0) {
    @{ status='not_needed'; checkedAt=(Get-Date -Format o); recipient=$Recipient; qualifyingCount=0 } |
        ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 0
}

$sentIds = @()
if (Test-Path -LiteralPath $statePath) {
    try { $sentIds = @((Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json).sentIds) } catch { $sentIds = @() }
}
$newItems = @($qualified | Where-Object { $_.id -notin $sentIds })
if ($newItems.Count -eq 0) {
    @{ status='already_sent'; checkedAt=(Get-Date -Format o); recipient=$Recipient; qualifyingCount=$qualified.Count } |
        ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 0
}

if (-not $env:RESEND_API_KEY) {
    @{ status='configuration_required'; checkedAt=(Get-Date -Format o); recipient=$Recipient; qualifyingIds=@($newItems.id); missing='RESEND_API_KEY' } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 0
}

$resendCommand = Get-Command resend -ErrorAction SilentlyContinue
if (-not $resendCommand) {
    @{ status='configuration_required'; checkedAt=(Get-Date -Format o); recipient=$Recipient; qualifyingIds=@($newItems.id); missing='resend CLI' } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 0
}

function Encode([string]$value) { [System.Net.WebUtility]::HtmlEncode($value) }
$cards = foreach ($item in $newItems) {
    $sourceLinks = foreach ($source in @($item.sources)) {
        $label = Encode ([string]$source.label)
        $url = Encode ([string]$source.url)
        '<a href="' + $url + '">' + $label + '</a>'
    }
    $price = if ($item.priceLabel) { [string]$item.priceLabel } else { '$' + ('{0:N0}' -f [decimal]$item.price) }
    '<section style="border:1px solid #d9dfdb;border-radius:8px;padding:16px;margin:14px 0">' +
    '<h2 style="margin:0 0 8px">' + (Encode ([string]$item.address)) + '</h2>' +
    '<p><b>' + (Encode $price) + '</b> · ' + (Encode ([string]$item.area)) + ' м² · ' + (Encode ([string]$item.land)) + ' сот.</p>' +
    '<p>' + (Encode ([string]$item.reason)) + '</p>' +
    '<p>' + ($sourceLinks -join ' · ') + ' · <a href="' + (Encode ([string]$item.map)) + '">Google Maps</a></p></section>'
}
$htmlFile = Join-Path $RunDirectory 'qualified-alert.html'
$html = '<!doctype html><html lang="uk"><meta charset="utf-8"><body style="font:15px/1.5 Arial,sans-serif;color:#162c35">' +
    "<h1>Знайдено об’єкт, що пройшов усі умови</h1>" +
    '<p>Щоденний пошук позначив наведені нижче оголошення як повністю перевірені. Перед завдатком повторно підтвердьте актуальність, документи й межі ділянки.</p>' +
    ($cards -join '') + '</body></html>'
$html | Set-Content -LiteralPath $htmlFile -Encoding UTF8

$from = if ($env:TERNOPIL_HOUSE_EMAIL_FROM) { $env:TERNOPIL_HOUSE_EMAIL_FROM } else { 'Ternopil House Search <onboarding@resend.dev>' }
$subject = 'Будинок у Тернополі відповідає всім умовам: ' + ($newItems.address -join '; ')
$rawKey = ($newItems.id | Sort-Object) -join '|'
$hash = [System.Security.Cryptography.SHA256]::HashData([System.Text.Encoding]::UTF8.GetBytes($rawKey))
$idempotencyKey = 'ternopil-house-' + ([Convert]::ToHexString($hash).ToLowerInvariant().Substring(0,32))
$sendOutput = & $resendCommand.Source emails send --from $from --to $Recipient --subject $subject --html-file $htmlFile --idempotency-key $idempotencyKey --quiet 2>&1
if ($LASTEXITCODE -ne 0) {
    @{ status='send_failed'; checkedAt=(Get-Date -Format o); recipient=$Recipient; qualifyingIds=@($newItems.id); error=($sendOutput -join "`n") } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 0
}

$allSent = @($sentIds + @($newItems.id) | Select-Object -Unique)
@{ sentIds=$allSent; updatedAt=(Get-Date -Format o) } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
@{ status='sent'; checkedAt=(Get-Date -Format o); recipient=$Recipient; qualifyingIds=@($newItems.id); response=($sendOutput -join "`n") } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
exit 0
