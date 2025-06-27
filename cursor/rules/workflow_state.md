# Workflow State

## 1. Phase
`Planning`   <!-- values: Planning · Implementation · Review · Maintenance -->

## 2. Current Task Pointer
- **todo file**  : `/todo.md`
- **next index** : 1   <!-- 1-based, top-to-bottom -->

## 3. Rules (AI MUST Follow)
1. **Always** read `todo.md` at the start of a run.  
2. Work on the **first unchecked task** only.  
3. After coding, run all tests (`pnpm test`).  
4. **Mark the task** `[x]` _only if tests pass_ and commit:  
````

git add .
git commit -m "feat: ✅ <task title>"

```
5. If blocked, change `[ ]` → `[!]` and ask the human for help.

> **Mnemonic**: _Read → Implement → Test → Mark → Commit → Repeat._

## 4. Log
| Timestamp (UTC+9) | Actor | Event |
|-------------------|-------|-------|
| 2025-06-22 11:00  | human | Initial files scaffolded (`project_config.md`, `workflow_state.md`) |
| 2025-06-22 11:05  | AI    | Parsed repository, waiting for `todo.md` generation |

*(Append new rows chronologically; keep the latest 50 lines, then archive to `logs/YYYY-MM-DD.md`.)*
```