"""Tier 1 — create/read Render AOVs on the Octane VideoPost (the solid part).

Render AOVs are BaseShader children wired through the VideoPost's indexed
inputs: ``SET_RENDERAOV_IN_CNT`` (count) and ``SET_RENDERAOV_INPUT_0 + N``
(slot N). Every helper here is **idempotent** — it finds an existing matching
AOV before creating a new one, so pressing Build twice never duplicates.
"""
from __future__ import annotations

from typing import Any, List, Optional

import c4d

from ..c4d_compat import octane_ids as ids
from .octane_probe import safe_set, safe_get


def read_existing(vp: Any) -> List[Any]:
    """All Render AOV shaders currently wired into the VideoPost."""
    out: List[Any] = []
    cnt = safe_get(vp, ids.SET_RENDERAOV_IN_CNT, 0) or 0
    for i in range(cnt):
        aov = safe_get(vp, ids.SET_RENDERAOV_INPUT_0 + i, None)
        if aov is not None:
            out.append(aov)
    return out


def _find_existing(vp: Any, aov_type: int, light_id: Any, name: str) -> Optional[Any]:
    for aov in read_existing(vp):
        if safe_get(aov, ids.RNDAOV_TYPE) != aov_type:
            continue
        if isinstance(light_id, int):
            if safe_get(aov, ids.RNDAOV_LIGHT_ID) == light_id:
                return aov
        else:
            # Sun/Env/None can't be matched by light id (param is an int) —
            # fall back to matching by the (unique) output name.
            if safe_get(aov, ids.RNDAOV_NAME) == name:
                return aov
    return None


def add_aov(vp: Any, probe: Any, aov_type: int, name: str,
            light_id: Any = None, undo: Any = None) -> Optional[Any]:
    """Create or update one Render AOV. Returns the shader, or None on failure."""
    if vp is None or aov_type is None:
        return None

    existing = _find_existing(vp, aov_type, light_id, name)
    if existing is not None:
        if undo is not None:
            undo.record_change(existing)
        safe_set(existing, ids.RNDAOV_NAME, name)
        safe_set(existing, ids.RNDAOV_ENABLED, True)
        return existing

    shader = None
    try:
        shader = c4d.BaseShader(probe.renderpass_type())
    except Exception as exc:  # noqa: BLE001
        print("[OLD] BaseShader(%s) raised: %s" % (probe.renderpass_type(), exc))
    if shader is None:
        print("[OLD] could not create Render AOV shader (type %s)" % probe.renderpass_type())
        return None

    safe_set(shader, ids.RNDAOV_TYPE, aov_type)
    if isinstance(light_id, int):
        safe_set(shader, ids.RNDAOV_LIGHT_ID, light_id)
    safe_set(shader, ids.RNDAOV_ENABLED, True)
    safe_set(shader, ids.RNDAOV_NAME, name)

    cnt = safe_get(vp, ids.SET_RENDERAOV_IN_CNT, 0) or 0
    vp.InsertShader(shader)
    if undo is not None:
        undo.record_new(shader)
    safe_set(vp, ids.SET_RENDERAOV_INPUT_0 + cnt, shader)
    safe_set(vp, ids.SET_RENDERAOV_IN_CNT, cnt + 1)

    # Verify the input count actually advanced. If it didn't, the count/slot
    # params (community-derived) are wrong on this build, and the shader would
    # silently overwrite slot 0 / never wire. Surface it instead of lying.
    if (safe_get(vp, ids.SET_RENDERAOV_IN_CNT, 0) or 0) != cnt + 1:
        print("[OLD] Render AOV wiring did not take (count param %s). Run the "
              "Inspector and verify SET_RENDERAOV_IN_CNT / INPUT_0."
              % ids.SET_RENDERAOV_IN_CNT)
        return None
    return shader
