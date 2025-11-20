param(
  [string]$Since = "2025-11-17T00:00:00Z",
  [string]$Until = "2025-11-18T00:00:00Z",
  [switch]$IncludeActions
)

$ErrorActionPreference = 'Stop'

function Get-Gh {
  param(
    [Parameter(Mandatory)][string]$Uri
  )
  if (-not $env:GITHUB_TOKEN -or $env:GITHUB_TOKEN.Trim().Length -lt 20) {
    throw "GITHUB_TOKEN is not set in this session. Set it: `$env:GITHUB_TOKEN='YOUR_TOKEN'"
  }
  $headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; 'X-GitHub-Api-Version'='2022-11-28'; 'User-Agent'='wellona-scan' }
  Invoke-RestMethod -Headers $headers -Uri $Uri -Method Get
}

Write-Host "[SCAN] GitHub activity from $Since to $Until (UTC)" -ForegroundColor Cyan

# Ensure logs directory
$logs = "C:\Wellona\wphAI\logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

# 1) Identify authenticated user
$me = Get-Gh -Uri "https://api.github.com/user"
Write-Host "[AUTH] User: $($me.login) (id=$($me.id))" -ForegroundColor Green

# 2) Enumerate repositories accessible to this token (includes private if permitted)
$aff = [System.Web.HttpUtility]::UrlEncode('owner,collaborator,organization_member')
$repos = @()
for ($page=1; $page -le 10; $page++) {
  $url = "https://api.github.com/user/repos?per_page=100&page=$page&affiliation=$aff&sort=updated&direction=desc"
  $batch = Get-Gh -Uri $url
  if (-not $batch -or $batch.Count -eq 0) { break }
  $repos += $batch
}

if (-not $repos -or $repos.Count -eq 0) {
  Write-Host "[WARN] No repositories were returned for this token." -ForegroundColor Yellow
}

$sinceDt = [DateTime]::Parse($Since)
$untilDt = [DateTime]::Parse($Until)

$allResults = @()

foreach ($r in $repos) {
  $owner = $r.owner.login
  $name  = $r.name
  $full  = $r.full_name

  # Commits
  $commits = @()
  try { $commits = Get-Gh -Uri "https://api.github.com/repos/$owner/$name/commits?since=$Since&until=$Until&per_page=100" } catch {}

  # PRs (filter by updated_at in window)
  $prs = @()
  try { $prs = Get-Gh -Uri "https://api.github.com/repos/$owner/$name/pulls?state=all&per_page=100&sort=updated&direction=desc" } catch {}
  $prs = @($prs | Where-Object { $_.updated_at -and ([DateTime]$_.updated_at) -ge $sinceDt -and ([DateTime]$_.updated_at) -lt $untilDt })

  # Issues (filter by updated_at in window)
  $issues = @()
  try { $issues = Get-Gh -Uri "https://api.github.com/repos/$owner/$name/issues?state=all&since=$Since&per_page=100" } catch {}
  $issues = @($issues | Where-Object { $_.pull_request -eq $null })

  # Releases
  $releases = @()
  try { $releases = Get-Gh -Uri "https://api.github.com/repos/$owner/$name/releases?per_page=100" } catch {}
  $releases = @($releases | Where-Object {
      ($_.created_at -and ([DateTime]$_.created_at) -ge $sinceDt -and ([DateTime]$_.created_at) -lt $untilDt) -or
      ($_.published_at -and ([DateTime]$_.published_at) -ge $sinceDt -and ([DateTime]$_.published_at) -lt $untilDt)
    })

  # Actions runs (optional)
  $runs = @()
  if ($IncludeActions) {
    try { $runs = Get-Gh -Uri "https://api.github.com/repos/$owner/$name/actions/runs?per_page=100" } catch {}
    if ($runs.workflow_runs) {
      $runs = @($runs.workflow_runs | Where-Object { $_.created_at -and ([DateTime]$_.created_at) -ge $sinceDt -and ([DateTime]$_.created_at) -lt $untilDt })
    } else { $runs = @() }
  }

  if ($commits.Count -or $prs.Count -or $issues.Count -or $releases.Count -or $runs.Count) {
    $allResults += [pscustomobject]@{
      repo      = $full
      commits   = $commits | ForEach-Object { [pscustomobject]@{ sha=$_.sha; message=$_.commit.message; author=$_.commit.author.name; date=$_.commit.author.date; url=$_.html_url } }
      prs       = $prs | ForEach-Object { [pscustomobject]@{ number=$_.number; title=$_.title; state=$_.state; created=$_.created_at; updated=$_.updated_at; merged=$_.merged_at; url=$_.html_url } }
      issues    = $issues | ForEach-Object { [pscustomobject]@{ number=$_.number; title=$_.title; state=$_.state; created=$_.created_at; updated=$_.updated_at; url=$_.html_url } }
      releases  = $releases | ForEach-Object { [pscustomobject]@{ tag=$_.tag_name; name=$_.name; created=$_.created_at; published=$_.published_at; url=$_.html_url } }
      actions   = $runs | ForEach-Object { [pscustomobject]@{ id=$_.id; name=$_.name; status=$_.status; conclusion=$_.conclusion; created=$_.created_at; url=$_.html_url } }
    }
  }
}

$outPath = Join-Path $logs "github_activity_$(Get-Date -Format yyyyMMdd)_nov17_window.json"
($allResults | ConvertTo-Json -Depth 6) | Out-File -FilePath $outPath -Encoding utf8

Write-Host "[DONE] Results saved to: $outPath" -ForegroundColor Green

# Print a short summary
if ($allResults.Count) {
  Write-Host "`nSummary:" -ForegroundColor Cyan
  foreach ($r in $allResults) {
    $c=$r.commits.Count; $p=$r.prs.Count; $i=$r.issues.Count; $rel=$r.releases.Count; $a=$r.actions.Count
    Write-Host (" - {0} -> commits:{1}  PRs:{2}  issues:{3}  releases:{4}  actions:{5}" -f $r.repo,$c,$p,$i,$rel,$a)
  }
} else {
  Write-Host "No activity found in the specified window." -ForegroundColor Yellow
}
