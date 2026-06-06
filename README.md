# Go Issue Agent

An agentic AI system that automatically processes GitHub issues from open-source Go projects and generates production-quality code changes.

---

## Overview

Takes a GitHub issue URL → Analyzes the problem → Builds a repository map → Plans a surgical fix → Applies changes → Validates with tests → Generates PR summary → Outputs patch and description.

### Proven Result

Tested on issue [#1315](https://github.com/spf13/cobra/issues/1315) — `LocalFlags().NFlag()` always returns 0 (open since 2021):

```diff
 if c.lflags.Lookup(f.Name) == nil && f != c.parentsPflags.Lookup(f.Name) {
     c.lflags.AddFlag(f)
+    if f.Changed {
+        c.lflags.Lookup(f.Name).Changed = true
+    }
 }
```

---

## Pipeline Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Stage 0    │───▶│   Stage 1    │───▶│   Stage 2    │───▶│   Stage 3    │
│  Repo Map   │    │ Fetch Issue  │    │Analyze Issue │    │ Explore Repo │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                    │
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────▼────────┐
│   Stage 8   │◀───│   Stage 7    │◀───│   Stage 6    │◀───│   Stage 5    │
│Save Outputs │    │ Generate PR  │    │  Validate    │    │  Apply Fix   │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### Key Design Decisions

**Structured fix representation** — the planner outputs JSON, not natural language:
```json
{
  "type": "insert_after",
  "target": "c.lflags.AddFlag(f)",
  "location_hint": "inside addToLocal closure in LocalFlags()",
  "code": "if f.Changed {\n\tc.lflags.Lookup(f.Name).Changed = true\n}"
}
```
The apply step is mechanical — find the target string, insert the code. No AI guesswork about location. This eliminates the class of bugs where the AI finds the right file but modifies the wrong part of it.

**Repository map (Stage 0)** — scans all `.go` files before processing any issue, extracting package names, function signatures, and imports. File selection uses this map instead of keyword grep.

**go.mod awareness** — reads existing dependencies before planning. Fixes never introduce new imports.

**Git stash rollback** — stashes before applying, pops automatically on failure. Repo is never left in a broken state.

---

## Quick Start

### Prerequisites

- Python 3.9+
- Go 1.21+
- Git
- API key for one of: Groq (free), Anthropic, or OpenAI

### Installation

```bash
# 1. Install dependencies
pip install groq requests

# Optional providers
pip install anthropic
pip install openai

# 2. Set API key
export GROQ_API_KEY=your_key_here         # default
# export LLM_PROVIDER=anthropic
# export ANTHROPIC_API_KEY=your_key_here
# export LLM_PROVIDER=openai
# export OPENAI_API_KEY=your_key_here

# 3. Clone a target repository
git clone https://github.com/spf13/cobra.git

# 4. Run
python run.py --issue https://github.com/spf13/cobra/issues/1315 --repo ./cobra
```

### Output

```
output/
├── patch.diff      # Git-style diff, ready to apply
└── pr_summary.md   # PR title and body, ready to submit
```

---

## Example Run

```
============================================================
GO ISSUE AGENT
============================================================
Issue: https://github.com/spf13/cobra/issues/1315
Repository: ./cobra
============================================================
[Stage 0] Building repository map... ✓ scanned 14 files
[Stage 1] Fetching issue... ✓
[Stage 2] Analyzing issue... ✓
[Stage 3] Exploring repo... ✓ identified 8 relevant files
[Stage 3.5] Analyzing dependencies... ✓ found 4 direct dependencies
[Validation] Checking target strings in plan... ✓
[Rollback] Stashing current state... ✓
[Stage 5] Applying fix...
  [DEBUG] Change type: insert_after
  [DEBUG] Target: c.lflags.AddFlag(f)
  [DEBUG] Applied insert_after successfully ✓
[Stage 5] Building... (attempt 1/3) ✓
[Stage 6] Validating changes...
  Running go test... ✓
  Running go fmt... ✓
  Running go vet... ✓
[Stage 7] Generating PR summary... ✓
[Stage 8] Saving outputs... ✓
============================================================
Issue: #1315
Files modified: 1
Build status: ✓
Validation status: passed
============================================================
```

---

## Project Structure

```
go-issue-agent/
├── run.py                    # CLI entry point
├── config.py                 # Models, limits, approved repos
├── tools.py                  # File I/O, grep, git helpers
├── requirements.txt
│
├── agent/
│   ├── pipeline.py           # Orchestrator
│   ├── build_repo_map.py     # Stage 0: repository structure analysis
│   ├── fetch_issue.py        # Stage 1: GitHub API
│   ├── analyze_issue.py      # Stage 2: AI issue analysis
│   ├── explore_repo.py       # Stage 3: file discovery
│   ├── plan_fix.py           # Stage 4: structured fix planning
│   ├── apply_fix.py          # Stage 5: mechanical fix application
│   ├── validate.py           # Stage 6: go test/fmt/vet
│   ├── generate_pr.py        # Stage 7: PR summary
│   └── llm_client.py         # Unified LLM interface (Groq/Anthropic/OpenAI)
│
└── prompts/
    ├── analyze.txt
    ├── plan.txt
    └── pr_summary.txt
```

---

## Approved Repositories

- `spf13/cobra`
- `gin-gonic/gin`
- `go-playground/validator`
- `golangci/golangci-lint`

---

## Security

- Repository whitelist — only approved repos processed
- No shell injection — all subprocess calls use list form
- API keys from environment only, never hardcoded
- File path validation — changes limited to repo directory

---

## Limitations

- Requires repository pre-cloned locally
- Handles focused, single-function bugs best
- Does not open actual PRs — generates patch and summary only

