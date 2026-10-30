# Reproduce the CPU simulation, speech, and local language model on Windows.
param([switch]$SkipAI, [string]$PythonExe = "")

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

function Check-Exit([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE"
    }
}

function Download-Verified([string]$url, [string]$path, [string]$sha256) {
    if (Test-Path -LiteralPath $path) {
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -eq $sha256) {
            Write-Host "Verified: $path"
            return
        }
    }
    New-Item -ItemType Directory -Force (Split-Path -Parent $path) | Out-Null
    & curl.exe -L --fail --retry 3 --continue-at - --output $path $url
    Check-Exit "Download $path"
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $sha256) {
        throw "SHA-256 mismatch for $path. Expected $sha256; got $actual"
    }
    Write-Host "Verified: $path"
}

function Checkout-Upstream([string]$url, [string]$path, [string]$commit) {
    if (-not (Test-Path -LiteralPath (Join-Path $path ".git"))) {
        if (Test-Path -LiteralPath $path) {
            throw "Directory exists without Git metadata: $path"
        }
        $stage = "$path.partial"
        $vendorRoot = [IO.Path]::GetFullPath((Join-Path $root "vendor"))
        $stageFull = [IO.Path]::GetFullPath($stage)
        if (-not $stageFull.StartsWith($vendorRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Unsafe temporary clone path: $stage"
        }
        if (Test-Path -LiteralPath $stage) {
            Remove-Item -LiteralPath $stage -Recurse -Force
        }
        & git clone --depth 1 $url $stage
        Check-Exit "Clone $url"
        Move-Item -LiteralPath $stage -Destination $path
    }
    $head = (& git -C $path rev-parse HEAD).Trim()
    Check-Exit "Inspect $path"
    if ($head -ne $commit) {
        & git -C $path fetch --depth 1 origin $commit
        Check-Exit "Fetch pinned commit $commit"
        & git -C $path checkout --detach FETCH_HEAD
        Check-Exit "Checkout $commit"
    }
    Write-Host "Pinned $path at $commit"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required. Install Git for Windows, then run this script again."
}
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    throw "curl.exe is required on Windows."
}

$python = Join-Path $root ".venv312\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    if ($PythonExe) {
        & $PythonExe -m venv (Join-Path $root ".venv312")
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv (Join-Path $root ".venv312")
    } else {
        throw "Python 3.12 is required. Install it with the Windows py launcher or pass -PythonExe."
    }
    Check-Exit "Create Python 3.12 virtual environment"
}
& $python -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version"
Check-Exit "Check Python 3.12"
& $python -c "import pip" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -m ensurepip --upgrade
    Check-Exit "Bootstrap pip in virtual environment"
}
& $python -m pip install -r (Join-Path $root "requirements-voice.txt")
Check-Exit "Install Python dependencies"

Checkout-Upstream "https://github.com/LuwuDynamics/xgoduck_rl.git" (Join-Path $root "vendor\xgoduck_rl") "fa621fc77ad9a05d69da13270e86118bdd3603fe"
Checkout-Upstream "https://github.com/LuwuDynamics/xgoduck_runtime_arduino.git" (Join-Path $root "vendor\xgoduck_runtime_arduino") "8837d5a3bc7cf3746f6da2b55c7b9191026b9838"

$voskZip = Join-Path $root "assets\speech\vosk-model-small-ru-0.22.zip"
Download-Verified "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip" $voskZip "961d5ff98a17f4aa6de69864d0aa71fa5bac682301d2b5d17a3f24c5c99a46d4"
$voskDir = Join-Path $root "assets\speech\vosk-model-small-ru-0.22"
if (-not (Test-Path -LiteralPath $voskDir)) {
    Expand-Archive -LiteralPath $voskZip -DestinationPath (Split-Path -Parent $voskZip)
}

if (-not $SkipAI) {
    $llamaZip = Join-Path $root "tools\llama.cpp\llama-b12001-bin-win-cpu-x64.zip"
    Download-Verified "https://github.com/ggml-org/llama.cpp/releases/download/b12001/llama-b12001-bin-win-cpu-x64.zip" $llamaZip "8b007136e5035c171c2fe6bcdcf074788a992894e06e188245d132223d177839"
    $server = Join-Path $root "tools\llama.cpp\llama-server.exe"
    if (-not (Test-Path -LiteralPath $server)) {
        Expand-Archive -LiteralPath $llamaZip -DestinationPath (Split-Path -Parent $llamaZip)
    }
    Download-Verified "https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q8_0.gguf?download=true" (Join-Path $root "assets\models\Qwen3-1.7B-Q8_0.gguf") "061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a"
}

& $python -m unittest discover -s tests -q
Check-Exit "Project tests"
if ($SkipAI) {
    Write-Host "Setup complete. Start: .\.venv312\Scripts\python.exe scripts\talk_to_duck.py --voice"
} else {
    Write-Host "Setup complete. Start: .\.venv312\Scripts\python.exe scripts\talk_to_duck.py --ai --voice"
}
