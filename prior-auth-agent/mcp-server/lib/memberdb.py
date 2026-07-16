"""Local SQLite member + prior-authorization queue — the cloud-free replacement
for an enterprise claims/EHR database.

Holds the structured, authoritative facts the agents look up: synthetic members
and a queue of pending prior-authorization (PA) requests, each carrying the
clinical detail a reviewer weighs against a coverage policy. Seeded once on first
use into a writable temp file.

SYNTHETIC teaching data only — fictional members, fictional requests. Not real
patients, not medical advice.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile

_DB = os.environ.get("MEMBER_DB") or os.path.join(tempfile.gettempdir(), "prior-auth.db")

# (id, name, plan, benefits summary)
_MEMBERS = [
    ("M-1001", "Jordan Rivera", "Gold PPO",
     "Advanced imaging covered with prior auth. PT benefit: 12 visits/condition/yr."),
    ("M-1002", "Sam Okafor", "Silver HMO",
     "Specialty drugs covered with prior auth + step therapy. Dermatology in-network."),
    ("M-1003", "Priya Nair", "Gold PPO",
     "Outpatient PT covered; extended courses require prior auth beyond 12 visits."),
    ("M-1004", "Alex Chen", "Silver HMO",
     "Advanced imaging covered with prior auth."),
    ("M-1005", "Riley Thompson", "Gold PPO",
     "Advanced imaging covered with prior auth."),
]

# (id, member_id, policy_id, service, clinical_note)  — the reviewer weighs the
# clinical_note against the policy's documented criteria. Designed to span the
# three outcomes: clear approve, clear deny, and pend-for-more-info.
_REQUESTS = [
    ("PA-5001", "M-1001", "CP-201", "Lumbar spine MRI (CPT 72148)",
     "48 y/o with low back pain for 3 months. Completed 8 weeks of physical therapy "
     "and NSAIDs with persistent pain; exam shows left L5 radiculopathy with reduced "
     "ankle reflex. No lumbar MRI in the past 2 years."),
    ("PA-5002", "M-1002", "CP-330", "Dermolimab (specialty biologic)",
     "Dermatologist-confirmed plaque psoriasis, BSA ~15%. Prescriber requests the "
     "biologic as first-line. No topical or systemic therapy tried yet. TB screen "
     "negative on file."),
    ("PA-5003", "M-1003", "CP-115", "Physical therapy — 10 additional visits",
     "Rotator-cuff rehab; 12-visit benefit used. Therapist reports the member 'is "
     "doing well' but no range-of-motion or outcome-score measures are attached. "
     "Requests more visits."),
    ("PA-5004", "M-1004", "CP-201", "Lumbar spine MRI (CPT 72148)",
     "History of prostate cancer, new unexplained weight loss and night pain. "
     "Physician suspects metastatic disease and requests urgent imaging."),
    # PA-5005 is engineered to make the critique→revise loop VISIBLE: strong,
    # detailed evidence for criteria 1–2 tempts a first-draft APPROVE, but the
    # note is silent on criterion 3 (prior imaging) — the correct answer is PEND,
    # and the Critic should catch a draft that misses it.
    ("PA-5005", "M-1005", "CP-201", "Lumbar spine MRI (CPT 72148)",
     "52 y/o with low back pain for 4 months. Completed 7 weeks of physical "
     "therapy plus NSAIDs with persistent left-leg radicular pain; exam shows "
     "positive straight-leg raise and diminished L5 sensation. New patient — "
     "first visit to this practice."),
]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS members(
                id TEXT PRIMARY KEY, name TEXT, plan TEXT, benefits TEXT);
            CREATE TABLE IF NOT EXISTS requests(
                id TEXT PRIMARY KEY, member_id TEXT, policy_id TEXT,
                service TEXT, clinical_note TEXT, status TEXT DEFAULT 'pending');
            CREATE TABLE IF NOT EXISTS determinations(
                request_id TEXT PRIMARY KEY, decision TEXT, rationale TEXT, ts TEXT);
            """
        )
        if not conn.execute("SELECT 1 FROM members LIMIT 1").fetchone():
            conn.executemany("INSERT INTO members(id,name,plan,benefits) VALUES (?,?,?,?)", _MEMBERS)
            conn.executemany(
                "INSERT INTO requests(id,member_id,policy_id,service,clinical_note) VALUES (?,?,?,?,?)",
                _REQUESTS)


def list_requests() -> list[dict]:
    """The queue of prior-auth requests (joined with member name/plan)."""
    init()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT r.id, r.member_id, m.name AS member_name, m.plan, r.policy_id, "
            "r.service, r.clinical_note, r.status "
            "FROM requests r JOIN members m ON m.id = r.member_id ORDER BY r.id").fetchall()
        return [dict(x) for x in rows]


def member_lookup(member_id: str) -> dict:
    """A member's plan + benefits (the structured, authoritative record)."""
    init()
    with _conn() as conn:
        row = conn.execute("SELECT id, name, plan, benefits FROM members WHERE id = ?",
                           (member_id,)).fetchone()
        return dict(row) if row else {"error": f"unknown member {member_id!r}"}


def submit_determination(request_id: str, decision: str, rationale: str, ts: str = "") -> dict:
    """Record a determination for a request (the irreversible WRITE)."""
    init()
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO determinations(request_id,decision,rationale,ts) VALUES (?,?,?,?)",
            (request_id, decision, rationale, ts))
        conn.execute("UPDATE requests SET status = ? WHERE id = ?", (f"determined:{decision}", request_id))
    return {"request_id": request_id, "decision": decision, "recorded": True}
