param([switch]$SelfTest)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $taskRoot
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$runDir = Join-Path $env:TEMP ('house_search\' + $stamp)
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$mutex = [Threading.Mutex]::new($false, 'Local\TernopilHouseSearchDaily')
if (-not $mutex.WaitOne(0)) { exit 0 }
try {
    $collectionDir = Join-Path $runDir 'sources'
    $collectorArgs = @((Join-Path $taskRoot 'collect.py'), '--out', $collectionDir)
    if ($SelfTest) { $collectorArgs += '--smoke' }
    & 'C:\Users\andri\AppData\Local\Programs\Python\Python310\python.exe' @collectorArgs 1> (Join-Path $runDir 'collection.log') 2> (Join-Path $runDir 'collection-errors.log')
    if ($LASTEXITCODE -ne 0) { throw 'Live collection failed; see collection-errors.log.' }
    if ($SelfTest) {
        $taskPrompt = "Automation smoke test only. The deterministic collector just fetched the real listing. Read $collectionDir\live-pages.json. Save smoke-verification.json in the working folder with URL, actual HTTP status, fetched timestamp, asking price and house area extracted from the current live data, plus source excerpt. Do not research other properties. State any errors truthfully. Reply in Ukrainian."
    } else {
        $taskPrompt = Get-Content -LiteralPath (Join-Path $taskRoot 'daily-prompt.md') -Raw -Encoding UTF8
        $taskPrompt += "`nDate/time on this computer: $(Get-Date -Format o). Current output folder: $runDir. Fresh public pages collected immediately before your run: $collectionDir\live-pages.json and discovered.json. Read them first. The collector is outside your command network sandbox; its HTTP results are fresh evidence. Use live web search for additional sites; do not label blocked direct access as sold."
    }
    $codexPath = Get-ChildItem -LiteralPath 'C:\Users\andri\AppData\Local\OpenAI\Codex\bin' -Filter codex.exe -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
    if (-not $codexPath) { throw 'The current Codex desktop CLI was not found.' }
    $finalPath = Join-Path $runDir 'result.md'
    $eventPath = Join-Path $runDir 'events.jsonl'
    $errorPath = Join-Path $runDir 'stderr.log'
    $taskPrompt | & $codexPath -a never --search exec --sandbox workspace-write -c sandbox_workspace_write.network_access=true --add-dir $runDir --skip-git-repo-check --ephemeral -C $taskRoot --json --output-last-message $finalPath - 1> $eventPath 2> $errorPath
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "Codex exited with code $code. See $errorPath" }
    if (-not (Test-Path -LiteralPath $finalPath)) { throw 'Missing Codex result.' }
    if (-not $SelfTest) {
        $htmlReport = Join-Path $runDir 'report.html'
        $jsonReport = Join-Path $runDir 'listings.json'
        $sourcesReport = Join-Path $runDir 'sources.html'
        if (-not (Test-Path -LiteralPath $htmlReport) -or -not (Test-Path -LiteralPath $jsonReport) -or -not (Test-Path -LiteralPath $sourcesReport)) { throw 'The daily analysis did not produce report.html, listings.json and sources.html; the previous report is preserved.' }
        if ((Get-Item -LiteralPath $htmlReport).Length -lt 500) { throw 'The generated HTML report is unexpectedly short.' }
        $reportData = Get-Content -LiteralPath $jsonReport -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $reportData.listings -or -not $reportData.sources) { throw 'The report lacks listings or source coverage; the previous report is preserved.' }
        $htmlText = Get-Content -LiteralPath $htmlReport -Raw -Encoding UTF8
        if ($htmlText -notmatch 'Актуальні сторінки' -or $htmlText -notmatch 'Що відсіяно або не включено' -or $htmlText -notmatch 'id="map"') { throw 'The report lacks the required tables or map.' }
        $previousBaseline = Join-Path $taskRoot 'baseline.json'
        if (Test-Path -LiteralPath $previousBaseline) { Copy-Item -LiteralPath $previousBaseline -Destination (Join-Path $runDir 'previous-baseline.json') -Force }
        $latestDir = Join-Path $taskRoot 'latest_report'
        New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
        & 'C:\Users\andri\AppData\Local\Programs\Python\Python310\python.exe' (Join-Path $taskRoot 'publish-report-assets.py') --report $htmlReport --source-root $runDir --destination-root $latestDir
        if ($LASTEXITCODE -ne 0) { throw 'The generated report references local assets that could not be published; the previous report is preserved.' }
        Copy-Item -LiteralPath $htmlReport -Destination (Join-Path $latestDir 'report.html') -Force
        Copy-Item -LiteralPath $htmlReport -Destination (Join-Path $latestDir 'index.html') -Force
        Copy-Item -LiteralPath $sourcesReport -Destination (Join-Path $latestDir 'sources.html') -Force
        $rootHtml = $htmlText.Replace('<head>', '<head><base href="latest_report/">')
        Set-Content -LiteralPath (Join-Path $taskRoot 'latest.html') -Value $rootHtml -Encoding UTF8 -NoNewline
        Set-Content -LiteralPath (Join-Path $taskRoot 'report.html') -Value $rootHtml -Encoding UTF8 -NoNewline
        Copy-Item -LiteralPath $sourcesReport -Destination (Join-Path $taskRoot 'sources.html') -Force
        Copy-Item -LiteralPath $jsonReport -Destination $previousBaseline -Force
        Copy-Item -LiteralPath $jsonReport -Destination (Join-Path $latestDir 'listings.json') -Force
        foreach ($pair in @(@('report.md','latest.md'), @('houses.geojson','houses.geojson'), @('changes.md','latest-changes.md'))) {
            $candidate = Join-Path $runDir $pair[0]
            if (Test-Path -LiteralPath $candidate) {
                Copy-Item -LiteralPath $candidate -Destination (Join-Path $taskRoot $pair[1]) -Force
                Copy-Item -LiteralPath $candidate -Destination (Join-Path $latestDir $pair[0]) -Force
            }
        }
        Copy-Item -LiteralPath $finalPath -Destination (Join-Path $taskRoot 'latest-summary.md') -Force
        & (Join-Path $taskRoot 'send-qualified-alert.ps1') -JsonReport $jsonReport -RunDirectory $runDir
    }
    @{ checkedAt=(Get-Date -Format o); exitCode=0; selfTest=[bool]$SelfTest; runDirectory=$runDir } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'last-run.json') -Encoding UTF8
    if (-not $SelfTest -and (Test-Path -LiteralPath (Join-Path $taskRoot '.git'))) {
        & git -C $taskRoot add --all
        if ($LASTEXITCODE -ne 0) { throw 'git add failed after publishing the report.' }
        & git -C $taskRoot diff --cached --quiet
        $diffCode = $LASTEXITCODE
        if ($diffCode -eq 1) {
            & git -C $taskRoot commit -m "Update house report $stamp"
            if ($LASTEXITCODE -ne 0) { throw 'git commit failed after publishing the report.' }
        } elseif ($diffCode -ne 0) {
            throw 'git diff failed while checking whether the report changed.'
        }
        & git -C $taskRoot push origin main
        if ($LASTEXITCODE -ne 0) { throw 'git push failed after publishing the report.' }
    }
} catch {
    $_ | Out-String | Set-Content -LiteralPath (Join-Path $runDir 'failure.txt') -Encoding UTF8
    @{ checkedAt=(Get-Date -Format o); error=$_.Exception.Message; runDirectory=$runDir } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'last-error.json') -Encoding UTF8
    @{ checkedAt=(Get-Date -Format o); exitCode=1; selfTest=[bool]$SelfTest; runDirectory=$runDir; error=$_.Exception.Message } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'last-run.json') -Encoding UTF8
    exit 1
} finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
exit 0
