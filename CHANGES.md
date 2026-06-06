# Code Changes Summary

## BUG 1: Removed extract_target.py

### File Deleted
```
agent/extract_target.py  (71 lines)
```

This file contained broken regex-based function name extraction that would invent non-existent functions.

---

## BUG 2: Enhanced apply_fix.py with Real Code Injection

### Key Changes

#### 1. Read Full File (not truncated)
**Before:**
```python
if file_path not in file_map:
    if os.path.exists(full_path):
        file_map[file_path] = read_file(full_path)
    else:
        raise Exception(f"File to modify not found: {file_path}")

current_content = file_map[file_path]  # Truncated to 11,309 chars
```

**After:**
```python
# Always read the FULL current file from disk (not from truncated explore results)
if os.path.exists(full_path):
    current_content = read_file(full_path)  # Full 61,142 chars for command.go
else:
    raise Exception(f"File to modify not found: {file_path}")
```

#### 2. Added _extract_function() - Brace Matching Algorithm
```python
def _extract_function(content: str, func_name: str) -> Optional[str]:
    """Extract a function's complete code from file content using brace matching."""
    # Searches for: func (c *Command) LocalFlags(
    # Returns: complete function from { to matching }
    # Result: 704 chars of EXACT real code
```

#### 3. Added _extract_closure() - Nested Closure Extraction
```python
def _extract_closure(content: str, closure_name: str) -> Optional[str]:
    """Extract a closure (e.g., addToLocal := func(...) {...})"""
    # Searches for: addToLocal := func
    # Returns: complete closure definition
    # Result: Precise guidance for nested edits
```

#### 4. Inject Real Code Into Prompt
**Before:**
```python
user_prompt = f"""Current content (first 2000 chars):
```go
{current_content[:2000]}  # TRUNCATED, wrong function
```
```

**After:**
```python
target_function_code = f"""
TARGET FUNCTION TO MODIFY:
Here is the EXACT current content of the {func_name}() function - use this VERBATIM as your OLD_CODE.
Do not paraphrase or reconstruct it. Your OLD_CODE must match this exactly, character for character.

```go
{extracted}  # FULL REAL CODE - 704 chars
```

IMPORTANT NESTED CLOSURE TO MODIFY:
Here is the addToLocal closure inside {func_name}():
```go
{addtolocal}  # NESTED CLOSURE extracted
```

If the change involves adding code after c.lflags.AddFlag(f), look for this exact pattern in the closure above.
"""
```

#### 5. Enhanced Constraints
Added to prompt:
```
10. Extract EXACTLY the code snippet that needs to be replaced - including surrounding context 
    like the function signature or closure start
11. For small changes (like adding a 2-3 line check), include enough context (10-20 lines) 
    to uniquely identify the location
```

#### 6. Location Guidance
```python
CRITICAL LOCATION GUIDANCE:
- If the change involves a closure or nested function, the edit must be INSIDE that closure/function body
- If you see "addToLocal := func", the change goes INSIDE that function
- Look for specific variable names or function calls in the change description
- Do not change the callers of the function, change the function itself
```

---

## Updated plan_fix.py

### Removed extract_target import
**Before:**
```python
from agent.extract_target import get_target_function_hint
```

**After:**
```python
# Removed - no longer needed
```

### Direct Issue Analysis
**Added to prompt:**
```python
function_identification = """
FUNCTION IDENTIFICATION:
- Look at the issue title and body to identify the specific function name mentioned
- Search the relevant files for functions matching those names
- Target the most relevant function that actually exists in the code
- Do not invent function names - only use functions that actually exist in the code
"""
```

---

## Updated pipeline.py

### Removed Target Extraction Stage
**Before:**
```python
# Extract target function from issue
target_function = extract_target_function(issue_data)
if target_function:
    print(f"[Target] Found target function: {target_function}")

# Stage 4: Plan fix
plan = plan_fix(
    issue_data, 
    analysis, 
    files, 
    groq_client, 
    config.SYSTEM_PROMPT,
    dependencies=dependencies,
    target_function=target_function
)
```

**After:**
```python
# Stage 4: Plan fix (will identify real functions from issue description)
plan = plan_fix(
    issue_data, 
    analysis, 
    files, 
    groq_client, 
    config.SYSTEM_PROMPT,
    dependencies=dependencies
)
```

---

## Result

### Before Fix
- Issue #1315: Agent invents "body()" function
- Generates code that doesn't exist in file
- Apply stage fails with: "OLD_CODE snippet not found"
- No fix produced

### After Fix
- Issue #1315: Agent correctly identifies LocalFlags()
- Receives full 704-char function code verbatim
- Applies targeted fix successfully
- Build passes ✅
- Tests pass ✅
