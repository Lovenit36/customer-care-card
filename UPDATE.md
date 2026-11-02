# V8 — Fixed Workspace and Maintenance Override

**1. Maintenance date override:** Choose a date in the care-plan form or chat panel. A chosen date supersedes the AI/document suggestion. Saving the card persists it. For an already saved card, select a date in the result chat panel and click Save date; card, PDF and calendar reminder reflect the update. No calendar dashboard is reintroduced.

**2. Fixed layout:** Header/sidebar stay in place; the form and chat scroll independently. On a completed card, aftercare/history and chat/reminders have separate scroll areas. On mobile, panels stack and scroll with reduced heights.

**3. Existing features retained:** Create Card, Update Existing Card, full dated history, PDF, .ics export, concise AI, Plancraft referral.

**4. Regression:** 37 automated tests passed. Chromium desktop/mobile tests use mocked server data (no live Sol API call).

**Mac install:** Back up .env and storage. Stop server, unzip fixes into the existing project, run `source .venv/bin/activate && PORT=3000 python3 server.py`. Safari hard refresh: Cmd+Shift+R.
