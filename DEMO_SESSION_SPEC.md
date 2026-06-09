# Demo Session API — Spec

## Overview

Generate a batch of 4 independent participant links on demand from the oepgv-docs site.
Each batch creates a fresh oTree session; prior batches remain live and unaffected.

---

## oTree REST API — What Actually Exists

oTree 5.11 has a built-in REST API. Since `AUTH_LEVEL = "STUDY"`, every request must include:

```
otree-rest-key: <value of OTREE_REST_KEY env var on the server>
```

Without this header the API returns 403.

### Relevant endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/sessions` | Create a new session → returns session code |
| `GET` | `/api/get_session/{code}` | Fetch session details including participant codes |

### Step 1 — Create session

```
POST https://sine-boardgame.fly.dev/api/sessions
otree-rest-key: SECRET

{
  "session_config_name": "data_sharing_game",
  "num_participants": 4
}
```

Response (does **not** include participant codes):
```json
{
  "code": "abc12345",
  "session_wide_url": "https://sine-boardgame.fly.dev/join/anon_code_here",
  "admin_url": "https://sine-boardgame.fly.dev/SessionStartLinks/abc12345"
}
```

### Step 2 — Fetch participant codes

```
GET https://sine-boardgame.fly.dev/api/get_session/abc12345
otree-rest-key: SECRET
```

Response includes a `participants` array:
```json
{
  "code": "abc12345",
  "participants": [
    { "id_in_session": 1, "code": "p1code123", ... },
    { "id_in_session": 2, "code": "p2code456", ... },
    { "id_in_session": 3, "code": "p3code789", ... },
    { "id_in_session": 4, "code": "p4codeabc", ... }
  ]
}
```

### Individual participant URLs

```
https://sine-boardgame.fly.dev/InitializeParticipant/{participant.code}
```

These are permanent and independent. Opening one does not affect the others.

---

## Two Link Options

| Option | What it is | When to use |
|--------|-----------|-------------|
| **4 individual links** | One unique `/InitializeParticipant/{code}` per participant | Each person gets their own link — you distribute them separately |
| **1 session-wide link** | Single `/join/{anon_code}` — first 4 visitors become the 4 participants | Easier to share but you can't control who gets which slot |

**Recommendation: 4 individual links** (matches "generate 4 new links" intent and avoids race conditions).

---

## Curl Test Plan

Run these against the live server once `OTREE_REST_KEY` is set as a Fly.io secret.

### 0. Check the secret is set

```bash
fly secrets list -a sine-boardgame
```

If `OTREE_REST_KEY` is not there, set it:

```bash
fly secrets set OTREE_REST_KEY=your-secret-here -a sine-boardgame
```

### 1. Verify REST API is reachable

```bash
curl -s https://sine-boardgame.fly.dev/api/otree_version \
  -H "otree-rest-key: your-secret-here"
```

Expected: `{"version": "5.11.2"}`
If 403: key is wrong or not set on server.

### 2. Create a session

```bash
SESSION=$(curl -s -X POST https://sine-boardgame.fly.dev/api/sessions \
  -H "Content-Type: application/json" \
  -H "otree-rest-key: your-secret-here" \
  -d '{"session_config_name": "data_sharing_game", "num_participants": 4}')

echo $SESSION
```

Expected: JSON with `code`, `session_wide_url`, `admin_url`.
Save the `code` value for step 3.

### 3. Fetch participant links

```bash
CODE="<paste code from step 2>"

curl -s https://sine-boardgame.fly.dev/api/get_session/$CODE \
  -H "otree-rest-key: your-secret-here" \
  | python3 -m json.tool
```

Expected: JSON with a `participants` array, each with a `code` field.
Individual links are: `https://sine-boardgame.fly.dev/InitializeParticipant/<participant_code>`

### 4. Confirm sessions are independent

Run step 2 again. Verify:
- A new `code` is returned
- Opening a link from batch 1 still works (not affected by creating batch 2)

---

## Implementation Plan (after curl tests pass)

### boardgame — no code changes needed
Only the Fly.io secret (`OTREE_REST_KEY`) needs to be set.

### oepgv-docs — two new files

**1. `app/api/demo-session/route.ts`** (Next.js server route)

- `POST` handler
- Calls `POST /api/sessions` on oTree → gets session code
- Calls `GET /api/get_session/{code}` → gets participant codes
- Returns `{ links: string[] }` (4 `InitializeParticipant` URLs)
- Keeps `OTREE_REST_KEY` server-side; the browser never sees it

Env vars needed in Vercel:
- `OTREE_REST_KEY` — same value as the Fly.io secret
- `BOARDGAME_URL` — defaults to `https://sine-boardgame.fly.dev` if unset

**2. `app/demo-session/page.tsx`** (client component)

- "Generate 4 Demo-Links" button
- Calls `/api/demo-session` (POST)
- Displays the 4 links with individual copy buttons
- Loading + error states
- Note: "Bereits laufende Sessions bleiben unberührt"

---

## Open Questions

1. Should the demo page be password-protected on the oepgv-docs side, or is it fine for anyone who finds the URL to generate sessions?
2. Do you want the page to also list currently-active sessions (via `GET /api/sessions`), or just generate-and-show?
3. Where should the page live in the oepgv-docs URL structure? (e.g. `/demo-session`, `/tools/demo`, …)
