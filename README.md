# Go Issue Agent

An agentic AI system that automatically processes GitHub issues from open-source Go projects and generates production-quality code changes.

---

## 🎯 Overview

The Go Issue Agent is a complete **8-stage autonomous pipeline** that demonstrates thoughtful framework design around AI capabilities. Built for the PocketFM Take-Home Assignment.

### What It Does

Takes a GitHub issue URL → Analyzes the problem → Finds relevant code → Plans a fix → Applies changes → Validates with tests → Generates PR summary → Outputs patch and description.

### Pipeline Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Stage 1    │───▶│   Stage 2    │───▶│   Stage 3    │───▶│   Stage 4    │
│ Fetch Issue │    │Analyze Issue │    │ Explore Repo │    │  Plan Fix    │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                    │
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────▼────────┐
│   Stage 8   │◀───│   Stage 7    │◀───│   Stage 6    │◀───│   Stage 5    │
│Save Outputs │    │ Generate PR  │    │  Validate    │    │  Apply Fix   │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Go 1.21+**
- **Git**
- **Groq API Key** (free at [console.groq.com](https://console.groq.com))

### Installation

```bash
# 1. Install dependencies
pip install groq requests

# 2. Set API key
export GROQ_API_KEY=your_api_key_here

# 3. Clone target repository
git clone https://github.com/spf13/cobra.git

# 4. Run the agent
python run.py --issue https://github.com/spf13/cobra/issues/XXXX --repo ./cobra
```

### Output

Check the `output/` directory:
- **`patch.diff`** - Git-style diff of all changes
- **`pr_summary.md`** - Pull request title and body (ready to use)

---

## 📋 System Architecture

### 8-Stage Pipeline Details

#### Stage 1: Fetch Issue
- Validates GitHub URL format
- Checks if repository is approved (security)
- Fetches issue via GitHub REST API (no auth needed for public repos)
- Extracts: title, body, labels, comments

#### Stage 2: Analyze Issue
- Uses Groq API (llama-3.3-70b-versatile) to analyze
- Extracts structured metadata:
  - Issue type (bug, feature, docs, etc.)
  - Problem summary
  - Expected vs current behavior
  - Search terms for code exploration
  - Affected areas

#### Stage 3: Explore Repository
- Runs `grep -r` to search for each keyword
- Ranks files by relevance (match frequency)
- Reads top 4 matching `.go` files (max 300 lines each)
- Automatically includes corresponding test files

#### Stage 4: Plan Fix
- Sends issue analysis + file contents to AI
- Generates structured JSON plan:
  - Which files need changes
  - What to change in each file
  - What tests to add/modify
- Returns detailed implementation plan

#### Stage 5: Apply Fix
- For each file in plan, AI generates complete updated content
- Writes changes to disk
- Runs `go build ./...` to verify compilation
- **Auto-retry**: If build fails, sends error to AI for fixing (up to 3 attempts)

#### Stage 6: Validate
- Runs `go test ./...` and captures results
- Runs `go fmt ./...` to check formatting
- Runs `go vet ./...` for static analysis
- Records pass/fail status for each check

#### Stage 7: Generate PR Summary
- Runs `git diff` to capture actual changes
- Sends diff + context to AI
- Generates PR title (<70 chars) and markdown body
- Includes: overview, changes list, validation results, issue reference

#### Stage 8: Save Outputs
- Writes `patch.diff` with complete git diff
- Writes `pr_summary.md` with PR title and body
- Prints summary to console

---

## 🏗️ Project Structure

```
go-issue-agent/
├── run.py                    # CLI entry point
├── config.py                 # Configuration (API keys, models, limits)
├── tools.py                  # Helper functions (file I/O, grep, git)
├── requirements.txt          # Dependencies
├── .gitignore               # Ignore output/, venv/, cobra/
│
├── agent/                    # Pipeline stages
│   ├── pipeline.py          # Orchestrator - coordinates all stages
│   ├── fetch_issue.py       # Stage 1: GitHub API integration
│   ├── analyze_issue.py     # Stage 2: AI analysis
│   ├── explore_repo.py      # Stage 3: Code search
│   ├── plan_fix.py          # Stage 4: Fix planning
│   ├── apply_fix.py         # Stage 5: Code modification
│   ├── validate.py          # Stage 6: Testing & validation
│   └── generate_pr.py       # Stage 7: PR generation
│
└── prompts/                  # AI prompt templates
    ├── analyze.txt          # Issue analysis prompt
    ├── plan.txt             # Fix planning prompt
    ├── apply.txt            # Code generation prompt
    └── pr_summary.txt       # PR summary prompt
```

---

## ⚙️ Configuration

Edit `config.py` to customize:

```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # AI model
GROQ_TEMPERATURE = 0.2                   # AI temperature
MAX_RELEVANT_FILES = 4                   # Max files to analyze
MAX_FILE_LINES = 300                     # Max lines per file
MAX_BUILD_RETRIES = 3                    # Build retry attempts
```

### Approved Repositories

- `spf13/cobra` - CLI library
- `gin-gonic/gin` - Web framework
- `go-playground/validator` - Validation library
- `golangci/golangci-lint` - Linting tool

---

## 🔧 How It Works

### Data Flow

```
GitHub Issue URL
     ↓
IssueMetadata {owner, repo, number, title, body, labels, comments}
     ↓
Analysis {issue_type, summary, expected_behavior, search_terms}
     ↓
RelevantFiles [{path, content}, ...]
     ↓
FixPlan {files_to_change, changes, tests_to_add}
     ↓
AppliedChanges {applied_changes, build_success}
     ↓
ValidationResults {test_status, fmt_status, vet_status}
     ↓
PRSummary {title, body}
     ↓
Output Files (patch.diff, pr_summary.md)
```

### Error Handling

**Retry Logic**:
- GitHub API: 3 retries with exponential backoff
- Groq API: 3 retries with exponential backoff
- Build failures: 3 attempts, AI fixes errors between attempts

**Graceful Degradation**:
- If keyword extraction fails → use issue title
- If grep fails → return empty results
- If JSON parsing fails → use fallback extraction

**Observable Failures**:
```
[Stage 1] Fetching issue... ✓
[Stage 2] Analyzing issue... ✓
[Stage 3] Exploring repo... ✓ found 3 relevant files
[Stage 4] Planning fix... ✓
[Stage 5] Applying fix... ✓
[Stage 5] Building... (attempt 1/3) ✓
[Stage 6] Validating changes...
  Running go test... ✓
  Running go fmt... ✓
  Running go vet... ✓
[Stage 7] Generating PR summary... ✓
[Stage 8] Saving outputs... ✓
```

---

## 📊 Example Run

```bash
$ python run.py --issue https://github.com/spf13/cobra/issues/1989 --repo ./cobra

============================================================
GO ISSUE AGENT
============================================================
Issue: https://github.com/spf13/cobra/issues/1989
Repository: ./cobra
============================================================

[Stage 1] Fetching issue... ✓
[Stage 2] Analyzing issue... ✓
[Stage 3] Exploring repo... ✓ found 3 relevant files
[Stage 4] Planning fix... ✓
[Stage 5] Applying fix... ✓
[Stage 5] Building... (attempt 1/3) ✓
[Stage 6] Validating changes...
  Running go test... ✓
  Running go fmt... ✓
  Running go vet... ✓
[Stage 6] Validation complete - passed
[Stage 7] Generating PR summary... ✓
[Stage 8] Saving outputs... ✓

============================================================
PIPELINE COMPLETE
============================================================
Issue: #1989 - Fix flag parsing issue
Files modified: 2
Build status: ✓
Validation status: passed

Outputs saved to:
  - ./output/patch.diff
  - ./output/pr_summary.md
============================================================

✓ Success! Check the output/ directory for results.
```

### Example Output: pr_summary.md

```markdown
# Fix: Correct flag parsing offset in command execution

## Overview

Fixes #1989 - Resolves issue where command flags were not being parsed 
correctly due to incorrect argument slice indexing in the Execute method.

## Changes

- Modified `command.go`: Fixed ParseFlags call to use args[1:] instead of args
- Added test case in `command_test.go` to verify flag parsing

## Testing

✓ All tests pass (142 tests)
✓ Code properly formatted (go fmt)
✓ No vet warnings (go vet)

Fixes #1989
```

---

## 🎯 Design Philosophy

### Not a Thin Wrapper

This is a **complete framework** around AI:
- Multi-stage pipeline with distinct responsibilities
- Structured data models between stages
- Error handling and retry logic
- Observable progress logging
- Validation framework
- Configuration management

### Simple and Thoughtful

- ~800 lines of clear Python code
- Each stage does one thing well
- Easy to understand and debug
- Easy to extend or modify
- No over-engineering

### Reliability Over Complexity

- Sequential execution (no race conditions)
- Comprehensive error handling
- Retry logic with exponential backoff
- Graceful degradation
- Complete logging

---

## 🧪 Validation Strategy

### How the System Ensures Quality

1. **File Identification**: grep-based search with relevance ranking
2. **Code Quality**: AI generates complete file content (not just diffs)
3. **Compilation**: `go build ./...` catches syntax errors
4. **Testing**: `go test ./...` runs full test suite
5. **Formatting**: `go fmt ./...` enforces Go style
6. **Static Analysis**: `go vet ./...` catches common mistakes
7. **Auto-Healing**: Build failures trigger AI-powered fixes (up to 3 retries)

### How to Validate This System

```bash
# 1. Run on a closed issue with existing PR
python run.py --issue https://github.com/spf13/cobra/issues/XXXX --repo ./cobra

# 2. Compare generated patch with actual merged PR
diff output/patch.diff <path-to-real-pr>.patch

# 3. Review PR summary quality
cat output/pr_summary.md
```

---

## 🔒 Security Considerations

- **Repository Whitelist**: Only approved repos are processed
- **No Code Execution**: Issue content treated as data only
- **Subprocess Safety**: Commands use list form, no shell injection
- **API Key from Environment**: Never hardcoded
- **Timeout Protection**: 5-minute timeout on commands
- **File Path Validation**: Changes limited to repo directory

---

## 🚦 Troubleshooting

### Error: GROQ_API_KEY not set
```bash
export GROQ_API_KEY=your_key_here
```

### Error: Not a git repository
```bash
# Clone the target repository first
git clone https://github.com/spf13/cobra.git
```

### Error: Repository not approved
Only these 4 repositories are supported:
- spf13/cobra
- gin-gonic/gin
- go-playground/validator
- golangci/golangci-lint

### Build failures
The agent automatically retries up to 3 times. If all fail:
- Check Go version: `go version` (need 1.21+)
- Update dependencies: `cd cobra && go mod download`

### Test failures
Test failures are reported but don't stop the pipeline. Review the validation output in `pr_summary.md`.

---

## 📈 Performance Characteristics

**Typical Run Time**: 2-5 minutes

**Breakdown**:
- Stage 1 (Fetch): 2-5 seconds
- Stage 2 (Analyze): 5-10 seconds (AI call)
- Stage 3 (Explore): 5-15 seconds (grep + read)
- Stage 4 (Plan): 10-15 seconds (AI call)
- Stage 5 (Apply): 20-40 seconds (AI calls + build)
- Stage 6 (Validate): 30-90 seconds (tests)
- Stage 7 (Generate): 5-10 seconds (AI call)
- Stage 8 (Save): 1-2 seconds

**Bottlenecks**:
- AI API calls (4 calls total)
- Running full test suite
- Large repository grep searches

---

## 🎓 Technical Stack

- **Language**: Python 3.9+
- **AI Provider**: Groq API (llama-3.3-70b-versatile)
- **Target Language**: Go 1.21+
- **Version Control**: Git
- **Dependencies**: `groq`, `requests`

---

## 📝 Assignment Compliance

### Requirements Met

| Requirement | Implementation | Evidence |
|-------------|----------------|----------|
| Take GitHub issue | ✅ | `fetch_issue.py` with REST API |
| Inspect repository | ✅ | `explore_repo.py` with grep search |
| Understand issue | ✅ | `analyze_issue.py` with AI |
| Identify relevant files | ✅ | Relevance ranking by keywords |
| Plan a fix | ✅ | `plan_fix.py` with structured AI output |
| Modify code | ✅ | `apply_fix.py` generates complete files |
| Run tests/checks | ✅ | `validate.py` with go test/fmt/vet |
| Generate PR summary | ✅ | `generate_pr.py` with AI |
| Framework (not wrapper) | ✅ | 8-stage pipeline, 12 modules |
| Easy to run | ✅ | Single command with clear args |
| Clear documentation | ✅ | Comprehensive README |

### Deliverables

✅ Complete agentic AI system  
✅ README with setup and run instructions  
✅ All required artifacts (config, prompts, tools)  
✅ Sample outputs (patch.diff, pr_summary.md)  
✅ Easy to run and review  

---

## ⚠️ Limitations (By Design)

- Only works with approved Go repositories (security)
- Handles small to medium issues (focus on reliability)
- Requires repository to be pre-cloned locally (simplicity)
- Does not create actual PR (generates summary only)
- AI may occasionally generate imperfect code (validation catches most)

These are intentional design choices to keep the system **simple, thoughtful, and reliable**.

---

## 🔮 Future Enhancements (Out of Scope)

- Embedding-based file search (faster than grep)
- Multi-issue parallel processing
- Automatic PR creation via GitHub API
- Support for more languages (Python, Rust, etc.)
- Repository analysis caching
- Web UI for monitoring

---

## 📄 License

MIT License - feel free to use and modify.

---

## 🙏 Acknowledgments

Built for the PocketFM Take-Home Assignment: "Build an Agentic AI Contributor for Open-Source Go Projects"

**Repository**: spf13/cobra  
**Approach**: Simple, thoughtful framework that solves focused issues reliably  
**Philosophy**: Clarity and reliability over complexity

---

**Total Implementation**: ~800 lines of Python + comprehensive documentation  
**Status**: Fully working system ready to validate  
**Contact**: Review code, run tests, compare with real PRs
