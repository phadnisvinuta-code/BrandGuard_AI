# BrandGuard AI — Round 2 MVP

BrandGuard AI is a small, explainable brand-governance prototype. It checks draft marketing text against explicitly entered approved facts and brand rules, shows evidence for findings, suggests edits, and keeps a human-controlled review status.

## Features implemented
- Dashboard with review counts and recent reviews
- Add approved product facts with source notes
- Add configurable exact-match brand rules
- Analyze marketing text using deterministic Python checks
- Evidence-linked findings with category, severity, explanation, suggestion, and confidence label
- Edit and re-check draft text
- Human-controlled Draft / Needs Changes / Approved status
- SQLite storage for facts, rules, and review history
- Health endpoint at `/api/health`

## Run locally (Windows + VS Code)
1. Install Python 3.10 or newer.
2. Extract this ZIP and open the `BrandGuard_AI_Round2` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt terminal and run:
   ```bat
   .venv\Scripts\activate.bat
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the app:
   ```bash
   python app.py
   ```
7. Open the local address printed in the terminal, usually `http://127.0.0.1:5000`.

## Demo scenario
Default approved fact: Insulated Bottle — Cooling duration: 12 hours.

Paste:
> Our revolutionary bottle keeps every drink cold for 24 hours!

Expected result: a potential unsupported product claim, the approved 12-hour fact as evidence, and an editable suggestion using the approved duration.

Then edit the draft to use 12 hours, re-check it, and set the review status manually.

## Important limitations
- This MVP uses deterministic text rules, not a connected LLM. Do not describe it as having advanced semantic AI.
- The checks only know the facts and rules configured in the database. “No issues found” does not mean a draft is guaranteed correct.
- It currently reviews text only; it does not inspect images, videos, PDFs, or publishing systems.
- Demo facts are synthetic. Replace them with authorised, verified information before real use.
- This is a prototype, not a legal or compliance guarantee.

## Suggested Round 3 improvements
1. Document upload and structured extraction of approved facts/rules, with a human confirmation step.
2. Versioned approved facts and an audit trail showing who changed facts and review decisions.
3. Multilingual/semantic review with uncertainty labels and tests that measure false positives and missed issues.

## GitHub and deployment
Create a public GitHub repository and push these project files. Deploy the Flask application to a Python-compatible host that supports your app's start command and persistent storage. Before submission, test the public URL in a private/incognito window and verify the full workflow. Some free hosts use ephemeral filesystems, so SQLite data may reset after redeployment; use a persistent database or hosted database if required by the selected host.

## Round 2 submission checklist
- [ ] Working project link tested by someone other than the developer
- [ ] Public/judge-accessible source repository
- [ ] Updated project PDF with actual implemented features and honest limitations
- [ ] Technology and implementation details
- [ ] Changes from Round 1 documented
- [ ] Three substantial Round 3 improvements
- [ ] Evidence of tests performed (do not invent results)
