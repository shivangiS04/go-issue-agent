# Go Issue Agent - Known Issues & Problems to Solve

## 🔴 CRITICAL ISSUES

### 1. AI Generates Incorrect Fixes Despite Receiving Correct Code

**Status:** OPEN  
**Priority:** P0 (Critical)  
**Component:** `agent/plan_fix.py`, `agent/apply_fix.py`

**Problem:**
The AI receives the EXACT correct function code (704 chars of LocalFlags()) but still generates the wrong fix. Instead of modifying the code inside the `addToLocal` closure, it wraps the `VisitAll()` calls with `if f.Changed` checks.

**Example:**
- **What AI generates:**
  ```diff
  -	c.Flags().VisitAll(addToLocal)
  +	c.Flags().VisitAll(func(f *flag.Flag) {
  +		if f.Changed {
  +			addToLocal(f)
  +		}
  +	})
  ```

- **What it should generate:**
  ```go
  addToLocal := func(f *flag.Flag) {
      if c.lflags.Lookup(f.Name) == nil && f != c.parentsPflags.Lookup(f.Name) {
          c.lflags.AddFlag(f)
          if f.Changed {  // ← ADD THIS
              c.lflags.Lookup(f.Name).Changed = true
          }
      }
  }
  ```

**Root Cause:**
The `plan_fix.py` stage generates vague change descriptions. The AI doesn't understand WHERE in the function to make changes.

**Current Description (Too Vague):**
```
"Modify the help command to prioritize local flags over persistent flags"
```

**Better Description Needed:**
```
"Inside the addToLocal closure in LocalFlags(), after c.lflags.AddFlag(f), add:
if f.Changed { c.lflags.Lookup(f.Name).Changed = true }"
```

**Solution Options:**
1. **Option A:** Provide few-shot examples in the prompt showing correct OLD_CODE/NEW_CODE patterns
2. **Option B:** Add structured guidance with line numbers and function signatures
3. **Option C:** Use a more sophisticated planning model that understands code structure
4. **Option D:** Implement a two-pass approach: first identify the exact location, then generate the fix

**Impact:**
- Agent produces syntactically correct code but semantically wrong fixes
- Build and tests pass, but the fix doesn't solve the actual problem

**Estimated Effort:** 2-4 hours

---

### 2. Groq API Rate Limiting (100k tokens/day)

**Status:** BLOCKING  
**Priority:** P1 (High)  
**Component:** External dependency

**Problem:**
```
Rate limit reached for model `llama-3.3-70b-versatile`
Limit: 100000 tokens per day (TPD)
Used: 99995, Requested: 630
Error: Please try again in 9m0s
```

**Root Cause:**
Using Groq free tier which has a 100k token/day limit. Testing and development consume tokens quickly.

**Solutions:**
1. **Short-term:** Wait for daily quota reset
2. **Medium-term:** Upgrade to Groq Dev Tier ($0.59 per 1M tokens)
3. **Long-term:** Add support for multiple LLM providers (OpenAI, Anthropic, local models)

**Workaround:**
Use environment variable to switch between providers:
```python
LLM_PROVIDER=openai  # or anthropic, groq, local
```

**Estimated Effort:** 2 hours to add multi-provider support

---

## 🟡 MEDIUM PRIORITY ISSUES

### 3. No Multi-File Fix Support

**Status:** OPEN  
**Priority:** P2 (Medium)  
**Component:** `agent/apply_fix.py`

**Problem:**
Agent can only modify one file at a time. Some fixes require changes across multiple files (e.g., changing a function signature and updating all callers).

**Example:**
```
Issue: Rename a function
Required changes:
- command.go: Rename function definition
- command_test.go: Update test calls
- other_commands.go: Update all references
```

**Current Behavior:**
- Only processes `files_to_change[0]`
- Other files in plan are ignored

**Solution:**
Loop through all files in `plan['files_to_change']` and apply fixes to each.

**Estimated Effort:** 1-2 hours

---

### 4. No Test Generation

**Status:** NOT IMPLEMENTED  
**Priority:** P2 (Medium)  
**Component:** New stage needed

**Problem:**
Agent can fix bugs but doesn't generate test cases to prevent regressions.

**Example:**
```
Fix: Add check for f.Changed in LocalFlags()
Missing: Test case that verifies NFlag() counts correctly
```

**Solution:**
Add Stage 6.5 that generates test cases:
```python
def generate_tests(fix, repo_path):
    # Analyze the fix
    # Generate test case that would fail without the fix
    # Write to *_test.go file
```

**Estimated Effort:** 4-6 hours

---

### 5. No Rollback Mechanism

**Status:** NOT IMPLEMENTED  
**Priority:** P2 (Medium)  
**Component:** `agent/pipeline.py`

**Problem:**
When a fix fails validation (tests fail, build breaks), the agent doesn't automatically rollback the changes. Repository is left in a broken state.

**Current Behavior:**
```
1. Apply fix
2. Build fails
3. Exit with error
4. Repository has broken code
```

**Desired Behavior:**
```
1. Apply fix
2. Build fails
3. Rollback changes
4. Try alternative fix
5. Or exit cleanly with original code
```

**Solution:**
Use git stash or branch:
```python
def apply_fix_with_rollback(repo_path, fix_func):
    original_branch = git.current_branch()
    try:
        git.checkout_branch("fix-attempt")
        fix_func()
        validate()
        git.merge("fix-attempt")
    except:
        git.checkout(original_branch)
        git.delete_branch("fix-attempt")
        raise
```

**Estimated Effort:** 2-3 hours

---

## 🟢 LOW PRIORITY ISSUES

### 6. No PR Creation Automation

**Status:** NOT IMPLEMENTED  
**Priority:** P3 (Low)  
**Component:** New stage needed

**Problem:**
Agent generates `patch.diff` and `pr_summary.md` but doesn't create actual pull requests.

**Current Workflow:**
```
1. Generate patch.diff
2. Generate pr_summary.md
3. User manually creates PR
```

**Desired Workflow:**
```
1. Generate patch.diff
2. Create branch
3. Commit changes
4. Push to GitHub
5. Create PR with generated summary
```

**Solution:**
Add Stage 9 using GitHub API:
```python
def create_pr(repo_path, issue_data, pr_summary):
    branch_name = f"fix-issue-{issue_data['number']}"
    # Create branch
    # Commit changes
    # Push
    # Create PR using GitHub API
```

**Estimated Effort:** 3-4 hours

---

### 7. No Commit Message Generation

**Status:** NOT IMPLEMENTED  
**Priority:** P3 (Low)  
**Component:** New stage needed

**Problem:**
When committing fixes, we need meaningful commit messages.

**Solution:**
Use LLM to generate commit message from fix description:
```
Input: "Added check for f.Changed in LocalFlags() to preserve flag state"
Output: "fix: preserve Changed state in LocalFlags() closure

When a flag is added to lflags, its Changed state is now preserved
by checking f.Changed and setting the flag's Changed attribute.

Fixes #1315"
```

**Estimated Effort:** 1-2 hours

---

### 8. Complex Nested Structure Modifications

**Status:** PARTIAL  
**Priority:** P3 (Low)  
**Component:** `agent/apply_fix.py`

**Problem:**
Extracting nested closures works, but modifying deeply nested structures (closures within closures) may not.

**Example:**
```go
func() {
    closure1 := func() {
        closure2 := func() {
            // Need to modify here
        }
    }
}
```

**Current Solution:**
- ✅ Extract function
- ✅ Extract one level of closure
- ❌ No support for deeper nesting

**Workaround:**
Make OLD_CODE large enough to include context (10-20 lines).

**Estimated Effort:** 2-3 hours for recursive closure extraction

---

## 🔵 ARCHITECTURAL IMPROVEMENTS

### 9. Structured Fix Representation

**Status:** IDEA  
**Priority:** P3 (Low)  
**Component:** `agent/plan_fix.py`

**Problem:**
Currently using natural language to describe fixes. This is ambiguous.

**Idea:**
Use structured representation:
```json
{
  "type": "insert_after",
  "target": "c.lflags.AddFlag(f)",
  "location": "addToLocal closure",
  "code": "if f.Changed { c.lflags.Lookup(f.Name).Changed = true }"
}
```

**Benefits:**
- Less ambiguous
- Easier to validate
- Can be translated to patches directly

**Estimated Effort:** 4-6 hours

---

### 10. Iterative Fix Refinement

**Status:** IDEA  
**Priority:** P3 (Low)  
**Component:** Entire pipeline

**Problem:**
Currently one-shot: plan → apply → validate. If it fails, we stop.

**Idea:**
Iterative refinement loop:
```
1. Generate initial fix
2. Validate
3. If tests fail:
   - Analyze failure
   - Generate refined fix
   - Retry (max 3 times)
4. If still fails, ask user for guidance
```

**Estimated Effort:** 6-8 hours

---

### 11. Caching and Incremental Analysis

**Status:** NOT IMPLEMENTED  
**Priority:** P3 (Low)  
**Component:** `agent/build_repo_map.py`

**Problem:**
Every run rebuilds the entire repo map from scratch, even if files haven't changed.

**Solution:**
- Cache repo map to `.kiro/repo_map.json`
- Only re-scan changed files (use git diff)
- Update cache incrementally

**Benefits:**
- Faster subsequent runs
- Less token usage (don't re-analyze same code)

**Estimated Effort:** 3-4 hours

---

## 📊 SUMMARY

| Priority | Count | Est. Total Effort |
|----------|-------|-------------------|
| P0 (Critical) | 1 | 2-4 hours |
| P1 (Blocking) | 1 | 2 hours |
| P2 (Medium) | 3 | 7-11 hours |
| P3 (Low) | 5 | 13-22 hours |
| **TOTAL** | **10** | **24-39 hours** |

---

## 🎯 RECOMMENDED APPROACH

### Immediate (Next Session)
1. **Fix Issue #1** (AI generates wrong fixes) - P0
   - Improve prompt with few-shot examples
   - Add structured location guidance
   - Test on 5+ issues

2. **Fix Issue #2** (API rate limits) - P1
   - Add multi-provider support
   - Or upgrade to paid tier

### Short-term (This Week)
3. **Fix Issue #3** (Multi-file support) - P2
4. **Fix Issue #5** (Rollback mechanism) - P2

### Medium-term (Next Week)
5. **Fix Issue #4** (Test generation) - P2
6. **Implement Issue #9** (Structured fixes) - P3

### Long-term (Future)
7. Remaining P3 issues
8. Documentation
9. Production hardening

---

## 📝 NOTES

### Testing Strategy
- Create test suite with 10+ real GitHub issues
- Include issues with known correct fixes
- Measure success rate: does agent generate correct fix?
- Track: build success, test success, semantic correctness

### Evaluation Metrics
```
Total issues attempted: N
Build passed: X/N
Tests passed: Y/N  
Correct fix: Z/N (manual review)

Success rate: Z/N
```

### Known Good Test Cases
1. Issue #1315 (LocalFlags Changed state)
2. Issue #1651 (Shadowed flags in help) - already fixed in repo
3. Issue #367 (Zsh completion) - needs investigation
4. Issue #2044 (Persistent run hooks) - needs investigation

---

**Last Updated:** 2026-06-05  
**Version:** 1.0  
**Maintainer:** Development Team
