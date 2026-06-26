"""Export generated items as a Canvas-importable QTI 1.2 package.

Canvas imports quizzes via an **IMS Content Package**: a ``.zip`` containing an
``imsmanifest.xml`` plus one or more QTI 1.2 assessment XML files. This module
builds that package from our internal item dicts (see :mod:`lib.generate`).

Per-type QTI mapping:
    * ``mcq``            -> ``response_lid`` (single) + ``render_choice`` + a
                           ``resprocessing`` block that scores the one right id.
    * ``multiple_answer``-> ``response_lid`` (multiple) + an ``AND`` of the
                           correct ids (and ``NOT`` of the wrong ones).
    * ``true_false``     -> ``response_lid`` with True/False choices.
    * ``short_answer``   -> ``response_str`` + a ``varequal`` per accepted answer.
    * ``essay``          -> ``response_str`` (no auto key; graded manually).

We build XML with :mod:`lxml.etree` when available, falling back to the stdlib
:mod:`xml.etree.ElementTree` so the module works in a bare environment.

Also exported: :func:`build_answer_key` (Markdown) and :func:`build_assignment`
(a brief + rubric as Markdown bytes).
"""
from __future__ import annotations

import io
import re
import zipfile

try:  # lxml gives prettier output; stdlib is a fine fallback.
    from lxml import etree as ET  # type: ignore
    _LXML = True
except Exception:  # pragma: no cover - depends on env
    import xml.etree.ElementTree as ET  # type: ignore
    _LXML = False


# --- small XML helpers ----------------------------------------------------

def _el(parent, tag, text=None, **attrs):
    """Create a child element with optional text + attributes."""
    if parent is None:
        e = ET.Element(tag)
    else:
        e = ET.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k, str(v))
    if text is not None:
        e.text = str(text)
    return e


def _tostring(root) -> bytes:
    if _LXML:
        return ET.tostring(root, xml_declaration=True, encoding="UTF-8",
                           pretty_print=True)
    # stdlib: add a declaration manually.
    body = ET.tostring(root, encoding="utf-8")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + body


def _slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", (s or "").strip()).strip("_")
    return (s or "assessment").lower()[:48]


def _ident(prefix: str, i: int) -> str:
    return f"{prefix}{i:04d}"


# --- QTI item builders ----------------------------------------------------

def _add_material(parent, text: str, *, html: bool = False):
    mat = _el(parent, "material")
    if html:
        _el(mat, "mattext", text or "", texttype="text/html")
    else:
        _el(mat, "mattext", text or "", texttype="text/plain")
    return mat


def _choice_item(item, ident, *, multiple: bool):
    """mcq / multiple_answer / true_false -> response_lid item element."""
    qit = _el(None, "item", ident=ident, title=_title_for(item))
    _add_meta(qit, item, "multiple_answers_question" if multiple
              else _meta_type(item))
    pres = _el(qit, "presentation")
    _add_material(pres, item.get("stem", ""), html=True)

    rcard = "Multiple" if multiple else "Single"
    rlid = _el(pres, "response_lid", ident=f"response_{ident}", rcardinality=rcard)
    rchoice = _el(rlid, "render_choice")

    options = item.get("options") or []
    answer_idents = []
    for j, opt in enumerate(options):
        aid = f"{ident}_a{j}"
        answer_idents.append(aid)
        rlabel = _el(rchoice, "response_label", ident=aid)
        _add_material(rlabel, opt, html=True)

    # resprocessing: score full points when the response matches the key.
    correct = item.get("correct")
    points = _points(item)
    resp = _el(qit, "resprocessing")
    out = _el(resp, "outcomes")
    _el(out, "decvar", maxvalue=str(points), minvalue="0",
        varname="SCORE", vartype="Decimal")

    cond = _el(resp, "respcondition")
    cond.set("continue", "No")
    if multiple:
        # AND of correct ids; NOT of every other id.
        correct_set = set(_correct_indices(item))
        and_el = _el(cond, "conditionvar")
        and_node = _el(and_el, "and")
        for j, aid in enumerate(answer_idents):
            if j in correct_set:
                _el(and_node, "varequal", aid, respident=f"response_{ident}")
            else:
                not_node = _el(and_node, "not")
                _el(not_node, "varequal", aid, respident=f"response_{ident}")
    else:
        idx = _single_correct_index(item)
        cvar = _el(cond, "conditionvar")
        target = answer_idents[idx] if 0 <= idx < len(answer_idents) else \
            (answer_idents[0] if answer_idents else "")
        _el(cvar, "varequal", target, respident=f"response_{ident}")
    _el(cond, "setvar", str(points), varname="SCORE", action="Set")
    return qit


def _short_answer_item(item, ident):
    qit = _el(None, "item", ident=ident, title=_title_for(item))
    _add_meta(qit, item, "short_answer_question")
    pres = _el(qit, "presentation")
    _add_material(pres, item.get("stem", ""), html=True)
    rstr = _el(pres, "response_str", ident=f"response_{ident}", rcardinality="Single")
    _el(rstr, "render_fib").set("prompt", "Box")

    points = _points(item)
    resp = _el(qit, "resprocessing")
    out = _el(resp, "outcomes")
    _el(out, "decvar", maxvalue=str(points), minvalue="0",
        varname="SCORE", vartype="Decimal")
    answers = item.get("correct") or []
    if not isinstance(answers, list):
        answers = [answers]
    for ans in answers:
        cond = _el(resp, "respcondition")
        cond.set("continue", "No")
        cvar = _el(cond, "conditionvar")
        ve = _el(cvar, "varequal", str(ans), respident=f"response_{ident}")
        ve.set("case", "No")
        _el(cond, "setvar", str(points), varname="SCORE", action="Set")
    return qit


def _essay_item(item, ident):
    qit = _el(None, "item", ident=ident, title=_title_for(item))
    _add_meta(qit, item, "essay_question")
    pres = _el(qit, "presentation")
    _add_material(pres, item.get("stem", ""), html=True)
    rstr = _el(pres, "response_str", ident=f"response_{ident}", rcardinality="Single")
    _el(rstr, "render_fib").set("prompt", "Box")
    # No auto resprocessing — graded manually. Declare the score variable so
    # Canvas knows the item's point value.
    points = _points(item)
    resp = _el(qit, "resprocessing")
    out = _el(resp, "outcomes")
    _el(out, "decvar", maxvalue=str(points), minvalue="0",
        varname="SCORE", vartype="Decimal")
    return qit


def _build_item(item, ident):
    t = item.get("type")
    if t == "mcq":
        return _choice_item(item, ident, multiple=False)
    if t == "multiple_answer":
        return _choice_item(item, ident, multiple=True)
    if t == "true_false":
        return _choice_item(item, ident, multiple=False)
    if t == "short_answer":
        return _short_answer_item(item, ident)
    if t == "essay":
        return _essay_item(item, ident)
    return None


# --- item metadata + helpers ----------------------------------------------

def _meta_type(item) -> str:
    return {
        "mcq": "multiple_choice_question",
        "true_false": "true_false_question",
        "multiple_answer": "multiple_answers_question",
        "short_answer": "short_answer_question",
        "essay": "essay_question",
    }.get(item.get("type"), "multiple_choice_question")


def _add_meta(qit, item, qtype: str):
    md = _el(qit, "itemmetadata")
    qti = _el(md, "qtimetadata")
    field = _el(qti, "qtimetadatafield")
    _el(field, "fieldlabel", "question_type")
    _el(field, "fieldentry", qtype)
    field2 = _el(qti, "qtimetadatafield")
    _el(field2, "fieldlabel", "points_possible")
    _el(field2, "fieldentry", str(_points(item)))


def _title_for(item) -> str:
    stem = re.sub(r"<[^>]+>", "", item.get("stem", "") or "")
    stem = stem.strip().replace("\n", " ")
    return (stem[:60] + "…") if len(stem) > 60 else (stem or "Question")


def _points(item) -> float:
    try:
        return float(item.get("points", 1))
    except Exception:
        return 1.0


def _correct_indices(item) -> list[int]:
    c = item.get("correct")
    if isinstance(c, list):
        return [int(x) for x in c if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return []


def _single_correct_index(item) -> int:
    if item.get("type") == "true_false":
        # options are ["True","False"]; correct is a bool.
        return 0 if bool(item.get("correct")) else 1
    idxs = _correct_indices(item)
    return idxs[0] if idxs else 0


# --- public API -----------------------------------------------------------

def build_qti_package(title: str, items: list[dict]) -> bytes:
    """Build an IMS Content Package (.zip) of a QTI 1.2 assessment.

    Args:
        title: the quiz/assessment title shown in Canvas.
        items: validated item dicts from :mod:`lib.generate`.

    Returns:
        The ``.zip`` bytes — ready for Canvas → Course → Import → QTI .zip.
    """
    title = title or "Generated Assessment"
    items = items or []
    assess_id = _slug(title)
    res_id = f"{assess_id}_res"
    xml_name = f"{assess_id}.xml"

    # --- assessment XML (questestinterop) ---
    root = _el(None, "questestinterop")
    assessment = _el(root, "assessment", ident=assess_id, title=title)
    amd = _el(assessment, "qtimetadata")
    f = _el(amd, "qtimetadatafield")
    _el(f, "fieldlabel", "cc_maxattempts")
    _el(f, "fieldentry", "1")
    section = _el(assessment, "section", ident="root_section")

    for i, item in enumerate(items, start=1):
        ident = _ident("item_", i)
        node = _build_item(item, ident)
        if node is not None:
            section.append(node)
    assessment_xml = _tostring(root)

    # --- imsmanifest.xml ---
    manifest = _build_manifest(assess_id, res_id, xml_name, title)

    # --- zip them into a content package ---
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr(xml_name, assessment_xml)
    return buf.getvalue()


def _build_manifest(assess_id: str, res_id: str, xml_name: str, title: str) -> bytes:
    NS = "http://www.imsglobal.org/xsd/imscp_v1p1"
    if _LXML:
        nsmap = {None: NS}
        man = ET.Element("manifest", nsmap=nsmap)
    else:
        ET.register_namespace("", NS)
        man = ET.Element("{%s}manifest" % NS)
    man.set("identifier", f"{assess_id}_manifest")

    def sub(parent, tag, **attrs):
        if _LXML:
            e = ET.SubElement(parent, tag)
        else:
            e = ET.SubElement(parent, "{%s}%s" % (NS, tag))
        for k, v in attrs.items():
            e.set(k, str(v))
        return e

    meta = sub(man, "metadata")
    sub(meta, "schema").text = "IMS Content"
    sub(meta, "schemaversion").text = "1.1.3"
    organizations = sub(man, "organizations")
    resources = sub(man, "resources")
    res = sub(resources, "resource", identifier=res_id,
              type="imsqti_xmlv1p2", href=xml_name)
    sub(res, "file", href=xml_name)

    if _LXML:
        return ET.tostring(man, xml_declaration=True, encoding="UTF-8",
                           pretty_print=True)
    body = ET.tostring(man, encoding="utf-8")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + body


def build_answer_key(title: str, items: list[dict]) -> str:
    """A human-readable Markdown answer key for the generated items."""
    title = title or "Generated Assessment"
    items = items or []
    lines = [f"# Answer key — {title}", ""]
    for i, item in enumerate(items, start=1):
        t = item.get("type", "?")
        stem = re.sub(r"<[^>]+>", "", item.get("stem", "") or "").strip()
        pts = _points(item)
        lines.append(f"## {i}. ({t}, {pts:g} pt) {stem}")
        options = item.get("options") or []
        if t in ("mcq", "multiple_answer", "true_false") and options:
            correct = _answer_label(item)
            for j, opt in enumerate(options):
                mark = "x" if j in set(_choice_correct_set(item)) else " "
                lines.append(f"- [{mark}] {chr(65 + j)}. {opt}")
            lines.append("")
            lines.append(f"**Correct:** {correct}")
        elif t == "short_answer":
            answers = item.get("correct") or []
            lines.append("**Accepted answers:** "
                         + ", ".join(str(a) for a in answers))
        elif t == "essay":
            lines.append("**Manually graded** (no fixed key).")
        rationale = (item.get("rationale") or "").strip()
        if rationale:
            lines.append(f"\n_Rationale:_ {rationale}")
        cit = item.get("citation") or {}
        src = " · ".join(x for x in [cit.get("source"), cit.get("loc")] if x)
        if src:
            lines.append(f"\n_Source:_ {src}")
        conf = item.get("confidence")
        if conf:
            lines.append(f"_Confidence:_ {conf}")
        lines.append("")
    return "\n".join(lines)


def _choice_correct_set(item) -> set:
    t = item.get("type")
    if t == "true_false":
        return {0} if bool(item.get("correct")) else {1}
    return set(_correct_indices(item))


def _answer_label(item) -> str:
    t = item.get("type")
    options = item.get("options") or []
    if t == "true_false":
        return "True" if bool(item.get("correct")) else "False"
    idxs = sorted(_choice_correct_set(item))
    labels = []
    for j in idxs:
        letter = chr(65 + j)
        opt = options[j] if 0 <= j < len(options) else ""
        labels.append(f"{letter}. {opt}")
    return "; ".join(labels) if labels else "(none)"


def build_assignment(brief: str, rubric: dict | None) -> bytes:
    """Render an assignment brief + rubric as Markdown bytes.

    Args:
        brief: the assignment prompt/instructions (plain text or Markdown).
        rubric: ``{title, criteria:[{criterion, levels_json}, ...]}`` or None.

    Returns:
        UTF-8 encoded Markdown bytes.
    """
    lines = ["# Assignment", "", (brief or "").strip(), ""]
    if rubric:
        lines.append(f"## Rubric — {rubric.get('title', 'Rubric')}")
        lines.append("")
        criteria = rubric.get("criteria") or []
        if criteria:
            for c in criteria:
                lines.append(f"### {c.get('criterion', 'Criterion')}")
                levels = c.get("levels_json")
                lines.append(_format_levels(levels))
                lines.append("")
        else:
            lines.append("_(no criteria defined)_")
    return "\n".join(lines).encode("utf-8")


def _format_levels(levels) -> str:
    """Best-effort render of a rubric criterion's levels (JSON or text)."""
    import json
    data = levels
    if isinstance(levels, (str, bytes)):
        try:
            data = json.loads(levels)
        except Exception:
            return str(levels)
    if isinstance(data, dict):
        return "\n".join(f"- **{k}**: {v}" for k, v in data.items())
    if isinstance(data, list):
        out = []
        for lvl in data:
            if isinstance(lvl, dict):
                label = lvl.get("label") or lvl.get("level") or lvl.get("name") or ""
                pts = lvl.get("points")
                desc = lvl.get("description") or lvl.get("desc") or ""
                head = f"- **{label}**" + (f" ({pts} pt)" if pts is not None else "")
                out.append(f"{head}: {desc}".rstrip(": "))
            else:
                out.append(f"- {lvl}")
        return "\n".join(out)
    return str(data) if data is not None else "_(no levels)_"
