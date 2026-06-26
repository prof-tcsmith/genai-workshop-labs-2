"""The Autonomous Course-Builder — an orchestrator + specialist agents over MCP.

An **Orchestrator** coordinates four specialists, who pass work between them (A2A):

  Researcher  — calls vector_search / course_lookup (over MCP) to gather grounded
                evidence; never writes.
  Item-writer — drafts assessment items grounded ONLY in that evidence.
  Critic      — judges each item for grounding + clarity; failures go back to the
                writer to revise (a capped critique→revise loop).
  Exporter    — calls export_qti (over MCP) to build the Canvas package — but ONLY
                after a human approves (the governance gate).

Every A2A message and tool call is recorded in an append-only **audit** trail. The
tools are reached over the network; the agents never import the backends.
"""
from __future__ import annotations

import json

from lib import itemschema, llm, mcp_client

CRITIQUE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "grounded": {"type": "boolean"},
        "clear": {"type": "boolean"},
        "ok": {"type": "boolean"},
        "notes": {"type": "string"},
    },
    "required": ["grounded", "clear", "ok", "notes"],
}


def _sources(passages: list[dict]) -> str:
    return "\n\n".join(f"[{p['doc']}] {p['text']}" for p in passages)


def _write_items(objective: str, passages: list[dict], rubric: dict, n: int) -> list[dict]:
    system = (
        "You are an expert instructional designer. Write assessment items GROUNDED "
        "ONLY in the provided passages — never invent facts, names, numbers, or "
        "definitions absent from them. Every item must be answerable from the passages "
        "alone and must cite the passage it came from (citation.source = the [doc] "
        "label). Use a mix of mcq, true_false, and short_answer. For choice items, "
        "'correct' holds option indices as strings (e.g. [\"0\"]); for short_answer, "
        "'correct' holds accepted answer strings. Respect the rubric. Respond using the "
        "provided JSON schema only."
    )
    user = (
        f"Learning objective: {objective}\n\n"
        f"Grading rubric: {json.dumps(rubric)}\n\n"
        f"Passages:\n{_sources(passages)}\n\n"
        f"Write {n} high-quality items."
    )
    out = llm.chat_json([{"role": "system", "content": system},
                         {"role": "user", "content": user}], itemschema.SCHEMA)
    items = [itemschema.validate(it) for it in (out.get("items") or [])]
    return [it for it in items if it]


def _critique(item: dict, passages: list[dict]) -> dict:
    system = (
        "You are a strict reviewer of quiz items. Decide if the item is (a) GROUNDED — "
        "fully answerable from the passages with no invented facts — and (b) CLEAR — "
        "unambiguous, with exactly one defensible answer for single-answer items. "
        "Reply with JSON {grounded, clear, ok, notes}; ok = grounded AND clear; notes "
        "give one concrete reason."
    )
    user = f"PASSAGES:\n{_sources(passages)}\n\nITEM:\n{json.dumps(_clean(item))}"
    v = llm.chat_json([{"role": "system", "content": system},
                       {"role": "user", "content": user}], CRITIQUE_SCHEMA)
    return {"ok": bool(v.get("ok")), "grounded": bool(v.get("grounded")),
            "clear": bool(v.get("clear")), "notes": (v.get("notes") or "").strip()}


def _revise(item: dict, verdict: dict, passages: list[dict]) -> dict | None:
    system = (
        "Revise the quiz item so it is fully grounded in the passages and unambiguous, "
        "keeping the same 'type'. Fix exactly what the critic flagged. Respond using the "
        "provided JSON schema only."
    )
    user = (f"PASSAGES:\n{_sources(passages)}\n\nITEM:\n{json.dumps(_clean(item))}\n\n"
            f"CRITIC NOTES: {verdict['notes']}")
    out = llm.chat_json([{"role": "system", "content": system},
                         {"role": "user", "content": user}], itemschema.ITEM_SCHEMA)
    return itemschema.validate(out)


def _clean(item: dict) -> dict:
    """Drop internal review fields before sending an item to a model or to qti."""
    return {k: v for k, v in item.items() if not k.startswith("_")}


def run_build(objective: str, n_items: int = 4, max_revisions: int = 2, log=None) -> dict:
    """Run the multi-agent build. Returns {items, a2a, audit, passages, objective}."""
    a2a: list[dict] = []
    audit: list[dict] = []

    def say(frm: str, to: str, content: str) -> None:
        a2a.append({"from": frm, "to": to, "content": content})
        audit.append({"event": "a2a", "detail": {"from": frm, "to": to, "content": content[:240]}})
        if log:
            log(frm, to, content)

    def act(event: str, detail) -> None:
        audit.append({"event": event, "detail": detail})

    # ORCHESTRATOR plans; RESEARCHER gathers grounded evidence over MCP.
    say("Orchestrator", "Researcher", f"Gather grounded passages for the objective: {objective}")
    passages = mcp_client.call_tool("vector_search", {"query": objective, "top_k": 6}) or []
    act("mcp_call", {"role": "researcher", "tool": "vector_search",
                     "args": {"query": objective, "top_k": 6}})
    rubric = mcp_client.call_tool("course_lookup", {"kind": "rubric"}) or {}
    act("mcp_call", {"role": "researcher", "tool": "course_lookup", "args": {"kind": "rubric"}})
    top = passages[0]["score"] if passages else 0
    say("Researcher", "Orchestrator", f"Found {len(passages)} passages (top similarity {top}).")
    if not passages:
        return {"items": [], "a2a": a2a, "audit": audit, "passages": [], "objective": objective}

    # ITEM-WRITER drafts grounded items.
    say("Orchestrator", "Item-writer", f"Draft {n_items} items grounded ONLY in those passages.")
    items = _write_items(objective, passages, rubric, n_items)
    act("items_drafted", {"n": len(items)})
    say("Item-writer", "Orchestrator", f"Drafted {len(items)} items.")

    # CRITIC reviews; failures go back to the writer (capped critique→revise loop).
    for rnd in range(max_revisions + 1):
        say("Orchestrator", "Critic", f"Review round {rnd + 1}: check grounding, clarity, alignment.")
        verdicts = [_critique(it, passages) for it in items]
        act("critic_round", {"round": rnd + 1, "passed": sum(v["ok"] for v in verdicts), "of": len(items)})
        failed_ix = [i for i, v in enumerate(verdicts) if not v["ok"]]
        say("Critic", "Orchestrator",
            f"{len(items) - len(failed_ix)}/{len(items)} passed."
            + (f" Revising {len(failed_ix)}." if failed_ix and rnd < max_revisions else ""))
        if not failed_ix or rnd == max_revisions:
            for it, v in zip(items, verdicts):
                it["_review"] = v
            break
        say("Orchestrator", "Item-writer", f"Revise {len(failed_ix)} item(s) per the critic's notes.")
        for i in failed_ix:
            revised = _revise(items[i], verdicts[i], passages)
            if revised:
                items[i] = revised
        act("revised", {"n": len(failed_ix)})

    return {"items": items, "a2a": a2a, "audit": audit, "passages": passages, "objective": objective}


def export(items: list[dict], title: str, audit: list | None = None) -> dict:
    """Exporter: build the QTI package over MCP. Call ONLY after a human approves."""
    res = mcp_client.call_tool("export_qti", {"title": title, "items": [_clean(it) for it in items]})
    if audit is not None:
        audit.append({"event": "approval_decision", "detail": {"by": "human", "decision": "approved"}})
        audit.append({"event": "mcp_call", "detail": {"role": "exporter", "tool": "export_qti",
                                                       "args": {"title": title, "n": len(items)}}})
        audit.append({"event": "outcome", "detail": {"status": "exported", "filename": res.get("filename")}})
    return res
