# Customer Care Card — V8 (Maintenance Override + Independent Scrolling)

An independent prototype, not an official Plancraft product. The craftsman has only **two main actions**: create a care card or update an existing card. For broader customer database and project management, the referral links to Plancraft.

## New in V8

- **Choose a maintenance date** in the main care plan OR in the chat panel. A craftsperson-selected date takes priority over any suggested date extracted from invoices, work reports or manuals. The date is added to the source text as a craftsperson override.
- **After saving a card**, use the date picker in the card’s AI/chat panel and click **Save date** to update the existing card immediately. The new date appears in the card, updated PDF and downloadable `.ics` reminder.
- **Fixed-height desktop workspace:** the main editor and AI chat stay side-by-side and scroll independently. The finished card’s aftercare/history column and its chat/reminders column also scroll independently; the overall page is no longer one giant scrolling document. On narrow screens, the columns stack and remain scrollable.
- Saved visit history, PDF download, customer privacy checks, and the Plancraft referral are preserved.

## What changed previously in V7

- Home/sidebar: 🪪 **Create Care Card**, 🔄 **Update Existing Card**. No customer directory, saved-customer selector or calendar page in the UI.
- Updating: upload the **existing Customer Care Card PDF**, or enter its **Card reference**. The app privately finds that particular record within your signed-in business workspace. Upload new work files, use AI extraction if authorised, review the new job and save. Your new visit appears **first**; the old visits remain below, labelled with the customer's name and service date.
- Every exported Care Card PDF now prints its exact reference near the top. It contains aftercare first, the **latest service**, then **earlier dated visits**, with their recorded work/parts/inspections/costs. The updated PDF replaces neither your original PDF on your device nor the old visits in storage; download and share the newly generated file.
- Older V6 PDFs did not contain an embedded reference. If the unmodified PDF filename is `customer-care-guide-xxxxxxxx.pdf` or `care-card-xxxxxxxx.pdf`, the app can also look up that eight-character prefix. A renamed PDF without a reference cannot be matched automatically. If you still have the old Card open, use **Add new work to this Card** instead.
- Clearer emoji icons in the home, navigation, input and output sections.
- A **Download calendar alert (.ics)** remains on the finished card whenever its next maintenance date has been reviewed and saved. The full calendar and appointment features are intentionally not exposed in the UI.
- The aftercare guide still aims for approximately 60% maintenance advice and 40% short work details. PDF and concise AI chat improvements from V6 remain.

## Install V8 fixes on your Mac

Back up `.env` and `storage` first. Stop the running server (`Control+C`). Extract the V8 fixes ZIP into **your existing** `~/Downloads/customer-care-card` folder. Then:

```bash
cd ~/Downloads/customer-care-card
unzip -o ~/Downloads/customer-care-card-v8-fixes.zip -d .
source .venv/bin/activate
python3 -m pip install -r requirements.txt
PORT=3000 python3 server.py
```

Open **http://localhost:3000** and hard-refresh Safari with `Cmd+Shift+R`.

**Do not replace `.env` or `storage/`.** Neither is in the fixes ZIP. Server-side storage is still necessary to preserve successive visits and restrict updates to the owning business. It is **not** presented as a customer-management database. Use the same browser session or signed-in business account that created the Card; uploading its PDF alone does not grant access to another account's private records.

## Simple end-to-end test

1. **Create Care Card:** enter the essential job details, optionally upload an invoice/report and use AI (only if your API project permits its configured model). Approve, save, and download the PDF.
2. **Update Existing Card:** upload *that* PDF or enter its printed Card reference. Click **Continue to new service**.
3. Upload the next work report or type the work completed, review the new aftercare, approve and **Save follow-up**.
4. The result should show the new visit first; expand **Previous work** for the older date and details.
5. Click **Download updated Care Card (PDF)**. The new PDF must contain the latest service, older visits, customer name/date, and reusable reference.
6. If a maintenance date is saved (whether from a document or your own selection), **Download calendar alert (.ics)** and import it into Apple or Google Calendar to receive a reminder after closing the app.

## Technical information and limitations

- Local app: Python HTTP backend, SQLite persistence, HTML/JS frontend, ReportLab PDFs, file parsing and evidence retrieval; server runs on port 3000 by default.
- The initial documents and service facts are not automatically modified by AI. AI outputs must be checked and approved before saving.
- Customer records stay on your private application server. There is **no Plancraft integration**.
- **AI access requires a model authorised for your OpenAI API project.** Automated tests use mock responses and do not validate your paid Sol credentials.
- Scanned PDFs without text extraction are not reliably readable unless separately supported; uploaded text-based PDFs and reports are the reliable path.
- `.ics` calendar alerts are downloaded files, not automatic background notifications or a two-way calendar sync.
- App-generated PDFs from older releases lacking both a reference and their original naming pattern may require reopening their saved record within the same existing session before updating.
- For real client information and public deployment, review authentication, privacy, lawful basis, retention, HTTPS and backups.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/check_v8_browser.py
```

The browser test uses mocked network responses and Chromium. The HTTP tests use temporary local storage and real PDF generation, but no paid AI calls.

## How to change maintenance dates

**During creation or updating:** After uploading a work document, the AI may suggest a date. In the main form under **Next maintenance date**, or in the panel beside chat, select your own date. Your date overrides the suggested one. Review/approve and save the card.

**After the card is saved:** Open its result screen and select a new date in **Update next maintenance date** in the chat panel, then click **Save date**. The card, its next PDF export and its `.ics` alert now use that date. The service history is preserved.

The chosen date is a craftsperson decision, *not a manufacturer-verified maintenance obligation*. Download the new PDF/.ics file to distribute the revised information. Already-imported events in external calendars are not synchronized automatically.

**Verification:** 37 automated backend tests passed; desktop/mobile Chromium interface tests passed using simulated API responses, including a document-suggested date superseded by a manually selected date. No live paid Sol call was run.
