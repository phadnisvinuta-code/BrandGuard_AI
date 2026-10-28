from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import re
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "brandguard-demo-secret-change-me")
DB_PATH = os.path.join(os.path.dirname(__file__), "brandguard.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                approved_value TEXT NOT NULL,
                source_note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                rule_text TEXT NOT NULL,
                find_text TEXT DEFAULT '',
                replacement_text TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                draft TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        fact_count = db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        rule_count = db.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
        now = datetime.now().isoformat(timespec="seconds")
        if fact_count == 0:
            db.executemany(
                "INSERT INTO facts(product, fact_key, approved_value, source_note, created_at) VALUES(?,?,?,?,?)",
                [
                    ("Insulated Bottle", "Cooling duration", "12 hours", "Synthetic demo fact approved for this prototype", now),
                    ("Insulated Bottle", "Product name", "Insulated Bottle", "Synthetic demo fact approved for this prototype", now),
                ],
            )
        if rule_count == 0:
            db.executemany(
                "INSERT INTO rules(category, rule_text, find_text, replacement_text, created_at) VALUES(?,?,?,?,?)",
                [
                    ("Terminology", "Use the approved product name 'Insulated Bottle'.", "thermal flask", "Insulated Bottle", now),
                    ("Required phrase", "Promotional copy must include the phrase 'Terms and conditions apply' when an offer is mentioned.", "limited time offer", "limited time offer. Terms and conditions apply.", now),
                    ("Tone", "Avoid absolute guarantees such as '100% guaranteed' unless explicitly approved.", "100% guaranteed", "designed to help keep drinks cold for up to 12 hours", now),
                ],
            )


def analyze_draft(draft):
    """Deterministic, explainable checks. Findings are review suggestions, not legal conclusions."""
    findings = []
    text = draft or ""
    lower = text.lower()

    # Compare numeric hour claims to approved duration facts.
    with get_db() as db:
        facts = db.execute("SELECT * FROM facts ORDER BY id").fetchall()
        rules = db.execute("SELECT * FROM rules ORDER BY id").fetchall()

    for fact in facts:
        if "hour" in fact["approved_value"].lower() and "cool" in (fact["fact_key"] + " " + fact["product"]).lower():
            approved_match = re.search(r"(\d+)\s*hours?", fact["approved_value"].lower())
            if approved_match:
                approved_hours = int(approved_match.group(1))
                claims = re.finditer(r"(\d+)\s*hours?", lower)
                for claim in claims:
                    claimed_hours = int(claim.group(1))
                    if claimed_hours > approved_hours:
                        start, end = claim.span()
                        sentence_start = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start)) + 1
                        candidates = [p for p in (text.find(".", end), text.find("!", end), text.find("?", end)) if p != -1]
                        sentence_end = min(candidates) + 1 if candidates else len(text)
                        flagged = text[sentence_start:sentence_end].strip() or text[start:end]
                        findings.append({
                            "category": "Potential unsupported product claim",
                            "severity": "High",
                            "flagged_text": flagged,
                            "reason": f"The draft states {claimed_hours} hours, but the approved fact available to this review says {approved_hours} hours.",
                            "evidence": f"{fact['product']} — {fact['fact_key']}: {fact['approved_value']}. Source note: {fact['source_note'] or 'No source note provided.'}",
                            "suggestion": f"Keeps drinks cold for up to {approved_hours} hours.",
                            "confidence": "Rule-based mismatch",
                        })
                        break

    # Apply configurable rules.
    for rule in rules:
        find_text = (rule["find_text"] or "").strip()
        if find_text and find_text.lower() in lower:
            # Avoid duplicating the absolute guarantee warning if already covered.
            already = any(f["flagged_text"].lower().find(find_text.lower()) >= 0 for f in findings)
            if not already:
                idx = lower.find(find_text.lower())
                start = max(text.rfind(".", 0, idx), text.rfind("!", 0, idx), text.rfind("?", 0, idx)) + 1
                candidates = [p for p in (text.find(".", idx + len(find_text)), text.find("!", idx + len(find_text)), text.find("?", idx + len(find_text))) if p != -1]
                end = min(candidates) + 1 if candidates else len(text)
                flagged = text[start:end].strip() or text[idx:idx + len(find_text)]
                findings.append({
                    "category": rule["category"],
                    "severity": "Medium",
                    "flagged_text": flagged,
                    "reason": f"This text matches a configured brand rule: {rule['rule_text']}",
                    "evidence": f"Brand rule: {rule['rule_text']}",
                    "suggestion": rule["replacement_text"] or "Please revise this wording according to the approved brand guidance.",
                    "confidence": "Exact rule match",
                })

    if not findings:
        findings.append({
            "category": "No configured rule violations found",
            "severity": "Low",
            "flagged_text": "No text was flagged by the configured checks.",
            "reason": "The current draft did not trigger any of the rules or fact-mismatch checks configured in this demo. This does not guarantee that every claim is correct.",
            "evidence": "Configured facts and rules were checked. Add more approved information to broaden the review.",
            "suggestion": "No automatic change suggested. Please continue with human review before publication.",
            "confidence": "Limited rule-based check",
        })
    return findings


@app.route("/")
def index():
    with get_db() as db:
        facts = db.execute("SELECT * FROM facts ORDER BY id DESC").fetchall()
        rules = db.execute("SELECT * FROM rules ORDER BY id DESC").fetchall()
        reviews = db.execute("SELECT * FROM reviews ORDER BY updated_at DESC LIMIT 8").fetchall()
        total_reviews = db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        needs_changes = db.execute("SELECT COUNT(*) FROM reviews WHERE status='Needs Changes'").fetchone()[0]
        approved = db.execute("SELECT COUNT(*) FROM reviews WHERE status='Approved'").fetchone()[0]
    return render_template("index.html", facts=facts, rules=rules, reviews=reviews,
                           total_reviews=total_reviews, needs_changes=needs_changes, approved=approved)


@app.route("/analyze", methods=["POST"])
def analyze():
    title = request.form.get("title", "").strip() or "Untitled content review"
    draft = request.form.get("draft", "").strip()
    if not draft:
        flash("Please enter some draft content before analyzing.", "error")
        return redirect(url_for("index"))
    findings = analyze_draft(draft)
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO reviews(title, draft, findings_json, status, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (title, draft, __import__("json").dumps(findings), "Needs Changes" if any(f["severity"] in ("High", "Medium") for f in findings) else "Draft", now, now)
        )
        review_id = cur.lastrowid
    return redirect(url_for("review_detail", review_id=review_id))


@app.route("/review/<int:review_id>")
def review_detail(review_id):
    import json
    with get_db() as db:
        review = db.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("index"))
    return render_template("review.html", review=review, findings=json.loads(review["findings_json"]))


@app.route("/review/<int:review_id>/update", methods=["POST"])
def update_review(review_id):
    status = request.form.get("status", "Draft")
    if status not in ("Draft", "Needs Changes", "Approved"):
        status = "Draft"
    draft = request.form.get("draft", "").strip()
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as db:
        existing = db.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not existing:
            flash("Review not found.", "error")
            return redirect(url_for("index"))
        if draft:
            findings = analyze_draft(draft)
            import json
            db.execute("UPDATE reviews SET draft=?, findings_json=?, status=?, updated_at=? WHERE id=?",
                       (draft, json.dumps(findings), status, now, review_id))
        else:
            db.execute("UPDATE reviews SET status=?, updated_at=? WHERE id=?", (status, now, review_id))
    flash("Review saved. Approval remains a human decision.", "success")
    return redirect(url_for("review_detail", review_id=review_id))


@app.route("/facts/add", methods=["POST"])
def add_fact():
    product = request.form.get("product", "").strip()
    fact_key = request.form.get("fact_key", "").strip()
    approved_value = request.form.get("approved_value", "").strip()
    source_note = request.form.get("source_note", "").strip()
    if not all([product, fact_key, approved_value]):
        flash("Product, fact name, and approved value are required.", "error")
    else:
        with get_db() as db:
            db.execute("INSERT INTO facts(product, fact_key, approved_value, source_note, created_at) VALUES(?,?,?,?,?)",
                       (product, fact_key, approved_value, source_note, datetime.now().isoformat(timespec="seconds")))
        flash("Approved fact added.", "success")
    return redirect(url_for("index") + "#knowledge")


@app.route("/rules/add", methods=["POST"])
def add_rule():
    category = request.form.get("category", "Terminology").strip()
    rule_text = request.form.get("rule_text", "").strip()
    find_text = request.form.get("find_text", "").strip()
    replacement_text = request.form.get("replacement_text", "").strip()
    if not rule_text or not find_text:
        flash("Rule description and text to detect are required for this demo rule.", "error")
    else:
        with get_db() as db:
            db.execute("INSERT INTO rules(category, rule_text, find_text, replacement_text, created_at) VALUES(?,?,?,?,?)",
                       (category, rule_text, find_text, replacement_text, datetime.now().isoformat(timespec="seconds")))
        flash("Brand rule added.", "success")
    return redirect(url_for("index") + "#knowledge")

@app.route("/try-demo", methods=["POST"])
def try_demo():

    import json


    title = "Demo: AquaPure Insulated Bottle"
    draft = "Our AquaPure Insulated Bottle keeps every drink cold for 24 hours!"

    findings = analyze_draft(draft)
    now = datetime.now().isoformat(timespec="seconds")

    with get_db() as db:
        cur = db.execute(
            """INSERT INTO reviews
            (title, draft, findings_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                title,
                draft,
                json.dumps(findings),
                "Needs Changes" if any(
                    f["severity"] in ("High", "Medium") for f in findings
                ) else "Draft",
                now,
                now
            )
        )
        review_id = cur.lastrowid

    return redirect(url_for("review_detail", review_id=review_id))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "product": "BrandGuard AI", "mode": "deterministic demo checks"})


init_db()

if __name__ == "__main__":
    app.run(debug=True)
