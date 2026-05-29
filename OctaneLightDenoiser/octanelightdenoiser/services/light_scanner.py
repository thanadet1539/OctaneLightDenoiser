"""Scan scene lights, manage Light Pass IDs / groups, and build the pass catalog.

Light grouping is the core idea: an Octane Light AOV is keyed by **Light Pass
ID (1..8)**, so lights that share an ID render as ONE combined pass. The Manage
tab assigns lights to IDs (= groups); the Build tab then shows one buildable
Light pass per active group (+ Sun + Env).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import c4d

from ..c4d_compat import octane_ids as ids
from ..models.pass_item import PassItem, LightInfo
from .octane_probe import iter_objects, safe_get, safe_set
from .undo_helper import UndoSession


# ============================================================ scene lights
def get_scene_lights(doc: Any, probe: Any) -> List[LightInfo]:
    """Every light in the scene: native C4D lights (c4d.Olight) AND any object
    carrying an Octane Light tag. The Octane Light tag (if present) holds the
    Light Pass ID; for a plain C4D light the tag is created on first Assign.
    """
    out: List[LightInfo] = []
    if doc is None:
        return out
    want = probe.lighttag_type()
    i = 0
    for obj in iter_objects(doc.GetFirstObject()):
        # find an existing Octane Light tag (if any)
        tag = None
        t = obj.GetFirstTag()
        while t:
            if t.GetType() == want:
                tag = t
                break
            t = t.GetNext()
        # a "light" = native C4D light, or anything already wearing an Octane Light tag
        is_light = tag is not None
        if not is_light:
            try:
                is_light = bool(obj.CheckType(c4d.Olight))
            except Exception:
                is_light = (obj.GetType() == getattr(c4d, "Olight", 5102))
        if not is_light:
            continue
        i += 1
        out.append(LightInfo(key="ML%d" % i, obj=obj, tag=tag, name=obj.GetName(),
                             light_id=(probe.read_light_pass_id(tag) if tag else None)))
    return out


def _ensure_light_tag(doc: Any, probe: Any, li: LightInfo, undo: Any) -> Any:
    """Return the light's Octane Light tag, creating + inserting it if missing."""
    if li.tag is not None:
        return li.tag
    if li.obj is None:
        return None
    want = probe.lighttag_type()
    t = li.obj.GetFirstTag()
    while t:
        if t.GetType() == want:
            li.tag = t
            return t
        t = t.GetNext()
    try:
        tag = c4d.BaseTag(want)
    except Exception as exc:  # noqa: BLE001
        print("[OLD] could not create Octane Light tag (%s): %s" % (want, exc))
        return None
    if tag is None:
        return None
    li.obj.InsertTag(tag)
    if undo is not None:
        undo.record_new(tag)
    li.tag = tag
    return tag


def selected_in_scene(doc: Any, lights: List[LightInfo]) -> set:
    """Keys of `lights` whose object is selected in the Object Manager.

    Uses the per-object active bit (BIT_ACTIVE) — the reliable selection flag —
    instead of identity-matching against GetActiveObjects (whose wrappers may
    not compare equal to cached references across calls).
    """
    sel = set()
    for li in lights:
        try:
            if li.obj is not None and li.obj.GetBit(c4d.BIT_ACTIVE):
                sel.add(li.key)
        except Exception:
            pass
    return sel


def group_by_id(lights: List[LightInfo]) -> Dict[int, List[LightInfo]]:
    groups: Dict[int, List[LightInfo]] = {}
    for li in lights:
        if isinstance(li.light_id, int):
            groups.setdefault(li.light_id, []).append(li)
    return groups


def next_free_id(lights: List[LightInfo]) -> Optional[int]:
    used = {li.light_id for li in lights if isinstance(li.light_id, int)}
    for n in range(1, ids.MAX_LIGHT_IDS + 1):
        if n not in used:
            return n
    return None


# ============================================================ ID mutations
def _write_pass_id(probe: Any, tag: Any, value: int) -> bool:
    """Write Light Pass ID using the probe's name-resolved param (or fallback)."""
    return safe_set(tag, probe.passid_write_param(tag), value)


def assign_id_to(doc: Any, probe: Any, lights: List[LightInfo], target_id: int) -> int:
    """Set `target_id` on every light in `lights` (= group them). Returns count."""
    if not lights or not isinstance(target_id, int):
        return 0
    n = 0
    with UndoSession(doc, label="Assign Light ID %d" % target_id) as undo:
        for li in lights:
            tag = _ensure_light_tag(doc, probe, li, undo)   # create tag if missing
            if tag is None:
                continue
            undo.record_change(tag)
            if _write_pass_id(probe, tag, target_id):
                li.light_id = target_id
                n += 1
    c4d.EventAdd()
    return n


def clear_ids(doc: Any, probe: Any, lights: List[LightInfo]) -> int:
    """Remove the Light Pass ID (write 0 = none). Returns count."""
    n = 0
    with UndoSession(doc, label="Clear Light IDs") as undo:
        for li in lights:
            if li.tag is None:
                continue
            undo.record_change(li.tag)
            if _write_pass_id(probe, li.tag, 0):
                li.light_id = None
                n += 1
    c4d.EventAdd()
    return n


def auto_assign_all(doc: Any, probe: Any, lights: List[LightInfo]) -> int:
    """Give each unassigned light its own unused ID (1..8). Returns count."""
    used = {li.light_id for li in lights if isinstance(li.light_id, int)}
    n, nid = 0, 1
    with UndoSession(doc, label="Auto-assign Light IDs") as undo:
        for li in lights:
            if li.light_id is not None:
                continue
            while nid in used and nid <= ids.MAX_LIGHT_IDS:
                nid += 1
            if nid > ids.MAX_LIGHT_IDS:
                break
            tag = _ensure_light_tag(doc, probe, li, undo)
            if tag is None:
                continue
            undo.record_change(tag)
            if _write_pass_id(probe, tag, nid):
                li.light_id = nid
                used.add(nid)
                n += 1
    c4d.EventAdd()
    return n


# ============================================================ build catalog
def build_catalog(doc: Any, probe: Any,
                  scene_lights: Optional[List[LightInfo]] = None,
                  group_names: Optional[Dict[int, str]] = None) -> List[PassItem]:
    """Build-tab passes: one Light pass per active group (+ Sun + Env) + standard."""
    if scene_lights is None:
        scene_lights = get_scene_lights(doc, probe)
    group_names = group_names or {}
    items: List[PassItem] = []

    groups = group_by_id(scene_lights)
    for gid in sorted(groups.keys()):
        members = groups[gid]
        # Neutral default ("Light <id>"): the user names groups themselves —
        # we don't borrow the light's object name (Key/Rim/Fill, etc.).
        # .strip() so a whitespace-only custom name falls back (matches the UI).
        name = (group_names.get(gid) or "").strip() or ("Light %d" % gid)
        items.append(PassItem(
            id="G%d" % gid, cat="LIGHT", source=name, light_id=gid,
            aov_type=ids.AOV_LIGHT,
            note="%d light%s" % (len(members), "s" if len(members) != 1 else ""),
        ))
    # NOTE: Sun / Environment light passes are intentionally NOT emitted yet —
    # their RNDAOV_LIGHT_ID enum value is unverified, so two such AOVs would
    # collide (render identical data). Add them back once confirmed via the
    # Inspector. Numbered groups (1..8) are the verified, working path.

    s = 0
    for cat, source, aov_type, required in ids.STANDARD_PASSES:
        s += 1
        items.append(PassItem(id="S%d" % s, cat=cat, source=source,
                              aov_type=aov_type, required=required))

    _mark_existing(doc, probe, items)
    return items


def _mark_existing(doc: Any, probe: Any, items: List[PassItem]) -> None:
    vp = probe.find_videopost(doc)
    if vp is None:
        return
    cnt = safe_get(vp, ids.SET_RENDERAOV_IN_CNT, 0) or 0
    types, light_ids = set(), set()
    for i in range(cnt):
        aov = safe_get(vp, ids.SET_RENDERAOV_INPUT_0 + i, None)
        if aov is None:
            continue
        t = safe_get(aov, ids.RNDAOV_TYPE)
        if t is not None:
            types.add(t)
        lid = safe_get(aov, ids.RNDAOV_LIGHT_ID)
        if t == ids.AOV_LIGHT and isinstance(lid, int):
            light_ids.add(lid)
    for it in items:
        if it.cat == "LIGHT" and isinstance(it.light_id, int):
            it.already = it.light_id in light_ids
        elif it.cat != "LIGHT" and it.aov_type is not None:
            it.already = it.aov_type in types
