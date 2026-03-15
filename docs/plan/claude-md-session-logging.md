# Session Logging

## Purpose
Every Claude Code session is logged for two reasons:
1. Open source transparency — anyone can see exactly how this project was built
2. Continuity — pick up where we left off between sessions

## Session Log Location
All session logs go in `docs/sessions/`

## At the START of Every Session

Create a new file: `docs/sessions/YYYY-MM-DD-HH-MM-session.md`

Write the following header immediately:

```markdown
# Session: [YYYY-MM-DD HH:MM]

## Prompt Provided
\`\`\`
[Paste the EXACT prompt you were given, verbatim, no edits]
\`\`\`

## Specs Referenced
- [List any spec files referenced in the prompt or during the session]

## Session Goal
[1-2 sentence summary of what this session is trying to accomplish]
```

## At the END of Every Session

Append the following to the same session log file:

```markdown
## Changes Made

### Files Created
| File | Purpose |
|------|---------|
| `path/to/file` | What it does |

### Files Modified
| File | What Changed |
|------|-------------|
| `path/to/file` | Summary of changes |

### Files Deleted
| File | Why |
|------|-----|
| `path/to/file` | Reason |

## Decisions Made
[List any judgment calls, trade-offs, or architectural decisions with rationale.]

## Problems Encountered
[Anything that didn't work the first time, workarounds, surprises in the data.]

## Current State
[What's working now that wasn't before this session]

## Next Steps
[What should the next session pick up on]

## Session Stats
- Duration: ~[X] minutes
- Files created: X
- Files modified: X
- DQ rules added: X (if applicable)
- Governance artifacts produced: [list] (if applicable)
```

## Rules
- The verbatim prompt capture is non-negotiable — copy it exactly as received, including typos
- Be honest in Problems Encountered — the failures are better content than the successes
- Decisions Made should capture the WHY, not just the WHAT
- If a session spans multiple specs, log all of them
- Don't sanitize or polish — raw is better for transparency
- Session logs are NEVER deleted, only appended to
- If you need to reference a previous session, check `docs/sessions/` first
