# Edivora one-time commit-author metadata cleanup. Windows PowerShell 5.1+ or PowerShell 7.
# REQUIREMENTS: Git, Python 3.12+, git-filter-repo via pip, and authenticated GitHub push access.
# Usage: .\Edivora_Commit_Email_Bereinigung.ps1          # local dry run
#        .\Edivora_Commit_Email_Bereinigung.ps1 -Execute # atomic force-with-lease push
# CAUTION: rewrites commit IDs for ALL local refs/heads and refs/tags. PR references and
# GitHub cached commits may remain visible and require GitHub Support intervention.
[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$repo = 'Cenn0/Edivora'
$noreply = '198997962+Cenn0@users.noreply.github.com'
$workspace = Join-Path ([IO.Path]::GetTempPath()) ('edivora-identity-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $workspace -Force | Out-Null
Write-Host "Localer Arbeitsordner: $workspace"

function Invoke-Checked([string]$Label, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Label fehlgeschlagen: Exitcode $LASTEXITCODE" }
}

try {
    Invoke-Checked 'Git-Version' { git --version }
    $python = (Get-Command py -ErrorAction SilentlyContinue)
    if ($python) {
        Invoke-Checked 'Python-Umgebung' { py -3.12 -m venv (Join-Path $workspace 'venv') }
    } else {
        Invoke-Checked 'Python-Umgebung' { python -m venv (Join-Path $workspace 'venv') }
    }
    $venvPython = Join-Path $workspace 'venv/Scripts/python.exe'
    $filterExe = Join-Path $workspace 'venv/Scripts/git-filter-repo.exe'
    $requirementsPath = Join-Path $workspace 'requirements.txt'
    # The pinned wheel hash is from the PyPI git-filter-repo 2.47.0 release.
    [IO.File]::WriteAllText($requirementsPath,
        "git-filter-repo==2.47.0 --hash=sha256:2cd04929b9024e83e65db571cbe36aec65ead0cb5f9ec5abe42158654af5ad83`n",
        [Text.UTF8Encoding]::new($false))
    Invoke-Checked 'git-filter-repo installieren' {
        & $venvPython -m pip install --disable-pip-version-check --no-deps --require-hashes -r $requirementsPath
    }

    $mirror = Join-Path $workspace 'repository.git'
    Invoke-Checked 'Repository spiegeln' { git clone --mirror "https://github.com/$repo.git" $mirror }
    Push-Location $mirror
    try {
        $before = @(git for-each-ref '--format=%(refname) %(objectname)' refs/heads refs/tags)
        if ($LASTEXITCODE -ne 0) { throw 'Git-Referenzen konnten nicht gelesen werden.' }
        if ($before.Count -eq 0) { throw 'Keine Branches/Tags vorhanden.' }
        $records = @(git log --all '--format=%an|%ae|%cn|%ce')
        if ($LASTEXITCODE -ne 0) { throw 'Git-Historie konnte nicht gelesen werden.' }
        $previousEmails = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($record in $records) {
            $parts = $record.Split('|')
            if ($parts.Count -ne 4) { continue }
            if ($parts[0] -eq 'Cenn0' -and $parts[1] -and $parts[1] -ne $noreply) { [void]$previousEmails.Add($parts[1]) }
            if ($parts[2] -eq 'Cenn0' -and $parts[3] -and $parts[3] -ne $noreply) { [void]$previousEmails.Add($parts[3]) }
        }
        if ($previousEmails.Count -eq 0) {
            Write-Host 'Keine zu ersetzenden Cenn0-Metadaten in den sichtbaren Git-Referenzen gefunden.'
            return
        }
        $mailmap = Join-Path $workspace 'mailmap.txt'
        $lines = @($previousEmails | ForEach-Object { "Cenn0 <$noreply> <$_>" })
        [IO.File]::WriteAllLines($mailmap, [string[]]$lines, [Text.UTF8Encoding]::new($false))
        Invoke-Checked 'Git-Historie lokal umschreiben' { & $filterExe --force --sensitive-data-removal --mailmap $mailmap }

        $after = @(git for-each-ref '--format=%(refname) %(objectname)' refs/heads refs/tags)
        if ($LASTEXITCODE -ne 0) { throw 'Rewritten refs fehlen.' }
        $beforeNames = @($before | ForEach-Object { ($_ -split ' ', 2)[0] } | Sort-Object)
        $afterNames = @($after | ForEach-Object { ($_ -split ' ', 2)[0] } | Sort-Object)
        if (($beforeNames -join "`n") -ne ($afterNames -join "`n")) { throw 'Referenzen haben sich unerwartet geändert.' }
        $remaining = @(git log --all '--format=%an|%ae|%cn|%ce') | Where-Object {
            $p = $_.Split('|')
            ($p.Count -eq 4) -and (
                (($p[0] -eq 'Cenn0') -and ($p[1] -ne $noreply)) -or
                (($p[2] -eq 'Cenn0') -and ($p[3] -ne $noreply))
            )
        }
        if ($remaining.Count -gt 0) { throw 'Nach dem Rewrite verblieben Cenn0-Commit-Metadaten mit alter Adresse.' }
        Write-Host "LOKAL BEREINIGT: $($previousEmails.Count) alte Adresse(n), $($before.Count) Branches/Tags."
        Write-Host 'Es wurden keine alten Adressen in der Konsolenausgabe ausgegeben.'

        if (-not $Execute) {
            Write-Host 'DRY RUN: Es wurde NICHT zu GitHub gepusht.'
            Write-Host 'Achtung: für -Execute muss die main-Ruleset-Force-Push-Sperre zunächst temporär angepasst werden.'
            return
        }
        # git-filter-repo removes origin by design; re-add it for a single atomic leased push.
        $remotes = @(git remote)
        if ($remotes -contains 'origin') {
            & git remote remove origin
            if ($LASTEXITCODE -ne 0) { throw 'Vorheriger Git-Remote konnte nicht entfernt werden.' }
        }
        & git remote add origin "https://github.com/$repo.git"
        if ($LASTEXITCODE -ne 0) { throw 'Git Remote konnte nicht angelegt werden.' }
        $leases = [Collections.Generic.List[string]]::new()
        $refspecs = [Collections.Generic.List[string]]::new()
        foreach ($row in $before) {
            $parts = $row.Split(' ', 2)
            if ($parts.Count -ne 2 -or $parts[1] -notmatch '^[a-f0-9]{40}$') { throw 'Ungültiger ursprünglicher Ref.' }
            $leases.Add("--force-with-lease=$($parts[0]):$($parts[1])")
            $refspecs.Add("$($parts[0]):$($parts[0])")
        }
        Write-Host 'GitHub Push: atomar und mit ref-spezifischem Force-with-Lease.'
        # Requires an authenticated git credential manager / gh auth setup-git.
        $pushOptions = @($leases.ToArray())
        $pushRefs = @($refspecs.ToArray())
        & git push --atomic @pushOptions origin @pushRefs
        if ($LASTEXITCODE -ne 0) { throw 'GitHub hat den Rewrite-Push abgelehnt; keine vollständige Bereinigung bestätigt.' }
        Write-Host 'Refs gepusht. Vorherige SHA-URLs, Pull-Request-Refs und Caches können weiterhin zugänglich sein.'
    } finally { Pop-Location }
} finally {
    Write-Host "Lokale Diagnose liegt unter: $workspace"
    Write-Host 'Prüfe anschließend das Repository, alle PR-Refs, Tags und GitHub-Caches. Für vollständige Entfernung ggf. GitHub Support einschalten.'
}