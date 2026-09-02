<#
.SYNOPSIS
    Installer for the Rigel (GPU) / XMRig (CPU) mining control setup.

.DESCRIPTION
    Downloads the latest Windows release of whichever miner(s) you choose
    directly from their official GitHub releases, and walks you through
    creating config.json with your wallet address.

.USAGE
    Right-click this file -> "Run with PowerShell"
    (or from an existing PowerShell window: .\install.ps1)

    If Windows blocks the script from running, open PowerShell as
    Administrator once and run:
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== Miner Rig Installer ===" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------
# 1. Ask what to install
# ---------------------------------------------------------------
Write-Host "What would you like to install on this machine?"
Write-Host "  1) GPU only  (Rigel)"
Write-Host "  2) CPU only  (XMRig)"
Write-Host "  3) Both"
$choice = Read-Host "Enter 1, 2, or 3"

$installGpu = ($choice -eq "1" -or $choice -eq "3")
$installCpu = ($choice -eq "2" -or $choice -eq "3")

if (-not $installGpu -and -not $installCpu) {
    Write-Host "No valid option selected. Exiting." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------
# 2. Helper: grab the Windows asset URL from a GitHub "latest release" API call
# ---------------------------------------------------------------
function Get-LatestWindowsAssetUrl {
    param(
        [string]$Owner,
        [string]$Repo,
        [string[]]$MustContain,   # all of these substrings must appear (case-insensitive)
        [string[]]$MustNotContain = @()
    )

    $apiUrl = "https://api.github.com/repos/$Owner/$Repo/releases/latest"
    $headers = @{ "User-Agent" = "miner-rig-installer" }
    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers

    foreach ($asset in $release.assets) {
        $name = $asset.name.ToLower()
        $matchesAll = $true
        foreach ($m in $MustContain) {
            if ($name -notlike "*$($m.ToLower())*") { $matchesAll = $false }
        }
        foreach ($n in $MustNotContain) {
            if ($name -like "*$($n.ToLower())*") { $matchesAll = $false }
        }
        if ($matchesAll) {
            return @{ Url = $asset.browser_download_url; Version = $release.tag_name; FileName = $asset.name }
        }
    }
    return $null
}

function Install-MinerFromZip {
    param(
        [string]$Name,
        [string]$Owner,
        [string]$Repo,
        [string[]]$MustContain,
        [string[]]$MustNotContain,
        [string]$DestDir
    )

    Write-Host "Looking up latest $Name release..." -ForegroundColor Yellow
    $asset = Get-LatestWindowsAssetUrl -Owner $Owner -Repo $Repo -MustContain $MustContain -MustNotContain $MustNotContain

    if ($null -eq $asset) {
        Write-Host "Could not find a matching Windows release asset for $Name." -ForegroundColor Red
        Write-Host "Check https://github.com/$Owner/$Repo/releases manually and download it yourself into $DestDir" -ForegroundColor Red
        return $false
    }

    Write-Host "Found $Name $($asset.Version): $($asset.FileName)" -ForegroundColor Green

    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    $zipPath = Join-Path $env:TEMP $asset.FileName

    Write-Host "Downloading..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $asset.Url -OutFile $zipPath

    Write-Host "Extracting to $DestDir..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath $DestDir -Force
    Remove-Item $zipPath

    Write-Host "$Name installed." -ForegroundColor Green
    return $true
}

# ---------------------------------------------------------------
# 3. Download whichever miners were selected
# ---------------------------------------------------------------
$binDir = Join-Path $root "bin"

if ($installGpu) {
    Install-MinerFromZip -Name "Rigel" -Owner "rigelminer" -Repo "rigel" `
        -MustContain @("win") -MustNotContain @("linux") `
        -DestDir (Join-Path $binDir "rigel")
}

if ($installCpu) {
    Install-MinerFromZip -Name "XMRig" -Owner "xmrig" -Repo "xmrig" `
        -MustContain @("win64") -MustNotContain @("linux", "macos") `
        -DestDir (Join-Path $binDir "xmrig")
}

# ---------------------------------------------------------------
# 4. Set up config.json if it doesn't exist yet
# ---------------------------------------------------------------
$configPath = Join-Path $root "config.json"

if (-not (Test-Path $configPath)) {
    Write-Host ""
    Write-Host "=== Wallet Setup ===" -ForegroundColor Cyan
    $btcAddress = Read-Host "Enter your BTC payout address (used for both GPU and CPU mining)"
    $workerName = Read-Host "Enter a worker/rig name for this machine (e.g. WindowsDesktop)"

    $config = Get-Content (Join-Path $root "config.example.json") -Raw | ConvertFrom-Json
    $config.worker_name = $workerName
    $config.gpu.wallet = "XEL:$btcAddress"
    $config.gpu.enabled = $installGpu
    $config.cpu.wallet = "BTC:$btcAddress"
    $config.cpu.enabled = $installCpu

    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath
    Write-Host "Wrote config.json" -ForegroundColor Green
} else {
    Write-Host "config.json already exists - leaving it as-is." -ForegroundColor Yellow
    Write-Host "Edit it by hand if you need to change wallet/worker name." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Install complete ===" -ForegroundColor Cyan
Write-Host "Run the control panel with:"
Write-Host "    python miner_control.py" -ForegroundColor White
Write-Host ""
Write-Host "(Requires Python 3 with tkinter, from https://python.org - tkinter is included by default on Windows installs)" -ForegroundColor Gray
