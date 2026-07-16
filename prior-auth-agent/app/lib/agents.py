"""The Prior-Authorization triage Case — an orchestrator + specialist agents over MCP.

An **Orchestrator** (deterministic Python) coordinates specialists that pass work
between them (A2A):

  Researcher — calls member_lookup + policy_search (over MCP) to gather the member's
               benefits and the applicable coverage criteria; never writes.
  Reviewer   — drafts a determination (approve / deny / pend) grounded ONLY in those
               retrieved criteria, citing the policy.
  Critic     — an LLM AS EVALUATOR: checks the determination for grounding +
               consistency; failures go back to the Reviewer to revise (a capped
               critique→revise loop).
  Case-worker — calls submit_determination (over MCP) to record the decision — but
               ONLY after a human (nurse / medical director) approves the gate.

Every A2A message and tool call is recorded in an append-only **audit** trail. The
tools are reached over the network; the agents never import the backends.

SYNTHETIC teaching data only. Not real patients. Not medical advice.
"""
from __future__ import annotations

import json

from lib import determination, llm, mcp_client


def _passages(passages: list[dict]) -> str:
    return "\n\n".join(f"[{p['doc']}] {p['text']}" for p in passages)


_SLOPPY_SYSTEM = (
    "You are a rushed prior-authorization reviewer with a huge queue. Skim the note; "
    "if things look mostly fine, approve. Assess AT MOST TWO criteria and assume "
    "anything the note doesn't mention is fine. Cite the policy (citation.source = "
    "the [doc] label). Respond using the provided JSON schema only."
)


def _review(request: dict, member: dict, passages: list[dict], sloppy: bool = False) -> dict | None:
    system = _SLOPPY_SYSTEM if sloppy else (
        "You are a prior-authorization nurse reviewer. Decide the request using ONLY "
        "the provided coverage-policy passages — never invent criteria, thresholds, or "
        "facts absent from them. Assess EACH relevant criterion (met = yes/no/unknown) "
        "with a short evidence quote from the clinical note. Then choose a decision:\n"
        "- approve: every required criterion is met;\n"
        "- deny: a required criterion is clearly not met and no exception applies;\n"
        "- pend: a required criterion cannot be determined from the note (missing "
        "documentation).\n"
        "Cite the policy you used (citation.source = the [doc] label). Respond using the "
        "provided JSON schema only. This is a synthetic exercise, not medical advice."
    )
    user = (
        f"MEMBER: {json.dumps(member)}\n\n"
        f"REQUEST: {request['service']} (policy {request['policy_id']})\n"
        f"CLINICAL NOTE: {request['clinical_note']}\n\n"
        f"COVERAGE POLICY PASSAGES:\n{_passages(passages)}"
    )
    out = llm.chat_json([{"role": "system", "content": system},
                         {"role": "user", "content": user}], determination.SCHEMA)
    return determination.validate(out)


def _critique(request: dict, det: dict, passages: list[dict]) -> dict:
    system = (
        "You are a strict medical-director reviewer AUDITING a draft determination. "
        "Work step by step: (1) enumerate EVERY numbered requirement in the policy "
        "passages (including 'no recent equivalent imaging' style requirements); "
        "(2) check the draft explicitly assessed each one with evidence quoted from "
        "the clinical note; (3) check the decision follows the rule: all required "
        "met → approve; a required one clearly not met → deny; a required one not "
        "determinable from the note → pend. GROUNDED = every assessment is supported "
        "by the passages and the note, nothing invented, no requirement skipped or "
        "assumed met without documentation. CONSISTENT = the decision follows the "
        "rule in (3). Reply with JSON {grounded, consistent, ok, notes}; ok = "
        "grounded AND consistent; notes name the specific requirement at fault."
    )
    user = (f"POLICY PASSAGES:\n{_passages(passages)}\n\n"
            f"CLINICAL NOTE: {request['clinical_note']}\n\n"
            f"DRAFT DETERMINATION:\n{json.dumps(det)}")
    v = llm.chat_json([{"role": "system", "content": system},
                       {"role": "user", "content": user}], determination.CRITIQUE_SCHEMA)
    return {"ok": bool(v.get("ok")), "grounded": bool(v.get("grounded")),
            "consistent": bool(v.get("consistent")), "notes": (v.get("notes") or "").strip()}


def _revise(request: dict, det: dict, verdict: dict, passages: list[dict]) -> dict | None:
    system = (
        "Revise the prior-authorization determination so it is fully grounded in the "
        "policy passages: assess EVERY required criterion with evidence from the note, "
        "then apply the rule — all required met → approve; a required one clearly not "
        "met → deny; a required one not determinable from the note (undocumented) → "
        "pend. Fix exactly what the auditor flagged. Respond using the provided JSON "
        "schema only."
    )
    user = (f"POLICY PASSAGES:\n{_passages(passages)}\n\n"
            f"CLINICAL NOTE: {request['clinical_note']}\n\n"
            f"DETERMINATION:\n{json.dumps(det)}\n\nAUDITOR NOTES: {verdict['notes']}")
    out = llm.chat_json([{"role": "system", "content": system},
                         {"role": "user", "content": user}], determination.SCHEMA)
    return determination.validate(out)


def run_triage(request: dict, max_revisions: int = 2, log=None, sloppy_reviewer: bool = False) -> dict:
    """Run the multi-agent triage for one PA request.

    ``sloppy_reviewer=True`` is a labelled DEMO FAULT (like Lab 3's sabotage
    sliders): the first draft uses a rushed reviewer prompt so the Critic can be
    seen catching it — revisions always use the careful prompt.
    Returns {determination, review, a2a, audit, passages, request, member}."""
    a2a: list[dict] = []
    audit: list[dict] = []

    def say(frm: str, to: str, content: str) -> None:
        a2a.append({"from": frm, "to": to, "content": content})
        audit.append({"event": "a2a", "detail": {"from": frm, "to": to, "content": content[:240]}})
        if log:
            log(frm, to, content)

    def act(event: str, detail) -> None:
        audit.append({"event": event, "detail": detail})

    # ORCHESTRATOR → RESEARCHER: gather the member record + the coverage criteria over MCP.
    say("Orchestrator", "Researcher",
        f"Gather the member record and coverage criteria for {request['id']} "
        f"({request['service']}).")
    member = mcp_client.call_tool("member_lookup", {"member_id": request["member_id"]}) or {}
    act("mcp_call", {"role": "researcher", "tool": "member_lookup",
                     "args": {"member_id": request["member_id"]}})
    query = f"{request['service']} — {request['policy_id']} medical necessity criteria"
    passages = mcp_client.call_tool("policy_search", {"query": query, "top_k": 6}) or []
    act("mcp_call", {"role": "researcher", "tool": "policy_search",
                     "args": {"query": query, "top_k": 6}})
    top = passages[0]["score"] if passages else 0
    say("Researcher", "Orchestrator",
        f"Member {member.get('name', '?')} ({member.get('plan', '?')}); "
        f"found {len(passages)} policy passages (top similarity {top}).")
    if not passages:
        return {"determination": None, "review": None, "a2a": a2a, "audit": audit,
                "passages": [], "request": request, "member": member}

    # ORCHESTRATOR → REVIEWER: draft a determination grounded in the criteria.
    say("Orchestrator", "Reviewer",
        "Draft a determination grounded ONLY in those criteria."
        + (" (⚠ demo fault: the reviewer is rushed)" if sloppy_reviewer else ""))
    if sloppy_reviewer:
        act("demo_fault", {"sloppy_reviewer": True})
    det = _review(request, member, passages, sloppy=sloppy_reviewer)
    if not det:
        return {"determination": None, "review": None, "a2a": a2a, "audit": audit,
                "passages": passages, "request": request, "member": member}
    act("determination_drafted", {"decision": det["decision"]})
    say("Reviewer", "Orchestrator", f"Draft decision: {det['decision'].upper()}.")

    # CRITIC (LLM as evaluator) reviews; failures go back to the Reviewer (capped loop).
    verdict = {}
    for rnd in range(max_revisions + 1):
        say("Orchestrator", "Critic",
            f"Audit round {rnd + 1}: is the {det['decision'].upper()} grounded and consistent?")
        verdict = _critique(request, det, passages)
        act("critic_round", {"round": rnd + 1, "ok": verdict["ok"],
                             "grounded": verdict["grounded"], "consistent": verdict["consistent"]})
        say("Critic", "Orchestrator",
            ("Passed." if verdict["ok"] else f"Not yet — {verdict['notes']}")
            + ("" if verdict["ok"] or rnd == max_revisions else " Sending back to revise."))
        if verdict["ok"] or rnd == max_revisions:
            break
        say("Orchestrator", "Reviewer", "Revise the determination per the auditor's notes.")
        revised = _revise(request, det, verdict, passages)
        if revised:
            det = revised
        act("revised", {"decision": det["decision"]})

    det["_review"] = verdict
    return {"determination": det, "review": verdict, "a2a": a2a, "audit": audit,
            "passages": passages, "request": request, "member": member}


def submit(request: dict, det: dict, audit: list | None = None) -> dict:
    """Case-worker: record the determination over MCP. Call ONLY after a human approves."""
    res = mcp_client.call_tool("submit_determination", {
        "request_id": request["id"], "decision": det["decision"],
        "rationale": det["rationale"]}) or {}
    if audit is not None:
        audit.append({"event": "approval_decision", "detail": {"by": "human", "decision": "approved"}})
        audit.append({"event": "mcp_call", "detail": {"role": "case-worker",
                     "tool": "submit_determination",
                     "args": {"request_id": request["id"], "decision": det["decision"]}}})
        audit.append({"event": "outcome", "detail": {"status": "recorded",
                     "request_id": request["id"], "decision": det["decision"]}})
    return res
