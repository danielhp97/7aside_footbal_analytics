# Data Sources

## 1. Garmin Connect

**Purpose:** Ground truth for game scores and dates.

**How to export:**
- Open Garmin Connect (web or app).
- Navigate to an activity → export as `.fit`, `.gpx`, or use the bulk export under Account Settings → Data Management → Export Your Data (delivers a ZIP with CSVs).
- Activity notes / descriptions can carry free-text scores like `3-2`.

**Expected fields we care about:**
| Field | Notes |
|-------|-------|
| `activity_date` | Date of the session |
| `activity_name` | Should contain "Football" or similar |
| `notes` / `description` | Free-text, user annotates score here |
| `duration_seconds` | Optional — could proxy session length |

**Parser location:** `src/football_analytics/parsers/garmin.py`

---

## 2. Facebook Messenger Group Chat

**Purpose:** Team rosters — who played and on which side.

**How to export:**
- Facebook Settings → Your Facebook Information → Download Your Information.
- Select **Messages**, format = **JSON**, date range covering all games.
- The chat JSON will be at `messages/inbox/<group-name>/message_1.json`.

**Message patterns to parse (examples):**
```
Team A: Alice, Bob, Carlos
Team B: David, Eve, Frank
```
or
```
Bibs: Alice Bob Carlos
Skins: David Eve Frank
```

**Parser location:** `src/football_analytics/parsers/messenger.py`

---

## Linking the two sources

Games are matched by **date**: a Garmin activity on 2025-01-10 is linked to the Messenger team selection closest to that date. Ambiguity is resolved manually for now.
