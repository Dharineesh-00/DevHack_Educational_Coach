# Track B — What We Built and Fixed

This document explains all the changes made to the frontend during Track B, in plain English.

---

## The Goal

Track B was about showing the student **what misconception they have** and **how many times they've repeated it** — displayed in the Agent Terminal after every code submission.

---

## What We Changed

### 1. The API URL is now configurable

Before, the frontend was hardcoded to always talk to `http://localhost:8000`. This broke when the backend moved to ngrok (a public URL that changes on every restart).

Now the URL is stored in a `.env` file:
```
VITE_API_URL=https://your-ngrok-url.ngrok-free.app
```
When the ngrok URL changes, you only update this one file — no code changes needed.

The `.env` file is gitignored so it never gets accidentally committed. A `.env.example` file is tracked in git so teammates know what variable to set.

---

### 2. The submit request now sends the right data

Before, the submit button was sending `{ language, code, user_id: 'user_42' }`.

Now it sends `{ user_id: 'test-user-1', problem_id: <slug>, code }` — matching what the backend actually expects. Each problem has a slug:
- Valid Parentheses → `valid-parentheses`
- Min Stack → `min-stack`
- Daily Temperatures → `daily-temperatures`
- Evaluate Reverse Polish Notation → `evaluate-rpn`

---

### 3. The Agent Terminal now shows the real Judge response

Before, the `[JUDGE]` line in the terminal always showed a hardcoded placeholder:
```
[JUDGE] Consensus reached. Generating Socratic hint.
```

Now it shows the actual Judge response text — the same Socratic hint that appears in the Tutor chat panel.

---

### 4. The Misconception block now always appears after submission

After every submission, the Agent Terminal shows a pinned block at the bottom:
```
Misconception  "Unclassified Misconception"  50% conf  line 1
```

- The misconception label comes from the backend's LLM analysis of the Critic's review
- Confidence shows how sure the AI is (0–100%)
- Line number points to where in the code the issue was spotted
- The block is always visible — it doesn't scroll away with the log lines

If the backend's LLM fails to classify the misconception (JSON parse error), it falls back to `"unclassified-misconception"` so the block still appears rather than being hidden.

---

### 5. Recurrence tracking — how many times you've made the same mistake

The backend's recurrence counter was broken (it only counted submissions that crashed, not all submissions). So we track recurrence on the frontend instead.

Every time you submit, the misconception ID is recorded. If the same ID comes back on a later submission:
- A recurrence count badge appears: `3x recurrence`
- If the last 2 submissions had the same misconception, a `⚠ streak` warning appears in amber

This resets to zero when you switch to a different problem.

---

### 6. Layout fixes

The terminal panel was too short (`30%` of screen height), so the misconception block was hidden behind the log lines.

- Terminal height increased from `30%` to `42%`
- Tutor chat panel reduced from `70%` to `58%` to compensate
- The misconception block is pinned at the bottom of the terminal (outside the scrollable log area) so it's always visible
- The duplicate badge strip that was showing the same info twice was removed

---

## Files Changed

| File | What changed |
|------|-------------|
| `frontend-new/src/App.jsx` | All UI and logic changes described above |
| `frontend-new/.env` | Created — holds the ngrok URL (gitignored) |
| `frontend-new/.env.example` | Created — shows teammates what variable to set |
| `frontend-new/.gitignore` | Added `.env` entries so secrets don't get committed |
| `backend/services/piston_runner.py` | Fixed Piston URL from local `127.0.0.1:2000` to public `https://emkc.org/api/v2/piston/execute` |

---

## Current Status

| Feature | Status |
|---------|--------|
| Critic / Defender / Judge in terminal | Working |
| Judge hint in Tutor chat | Working |
| Misconception block visible | Working (shows `unclassified-misconception` until backend LLM JSON is fixed) |
| Recurrence count | Working (tracked on frontend) |
| Streak warning | Working |
| Piston code execution | Working |

---

## One Known Issue

The backend's misconception LLM prompt sometimes returns JSON wrapped in markdown code fences (` ```json ... ``` `) which causes the JSON parser to fail. When that happens, the ID falls back to `"unclassified-misconception"`. This is a backend fix — the frontend handles it gracefully.
