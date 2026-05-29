"""Tier 2 — per-pass OIDN denoise graph in the Output-AOV Compositor.

HONEST STATUS
-------------
The Output/Composite-AOV input pins, the "Open Image Denoiser" blend-layer
node, and its albedo/normal/source parameter IDs are **not** in the public
Octane ID map and are unverified on this build. Wiring them blind risks a
broken graph — so this module does NOT guess. It instead guarantees the
*inputs* OIDN needs (the Light AOVs + Denoise Albedo/Normal Render AOVs are
created by aov_builder in Tier 1) and reports precisely what remains.

Two supported finishing paths:

  (A) Template-merge (recommended). Hand-build ONE
        RenderOutputAOV -> Open Image Denoiser (+albedo +normal) -> OutputAOV
      group once in the Output-AOV Compositor, save the scene as
      ``templates/oidn_group.c4d``. ``build`` then merges it so you only repoint
      the source per pass (1-2 clicks each) instead of wiring from scratch.

  (B) Programmatic. After the Inspector confirms the composite input
      count/base + the OIDN node + its param ids, implement ``add_output_aov``
      here mirroring ``aov_builder.add_aov``.
"""
from __future__ import annotations

import os
from typing import Any, List

import c4d

from .octane_probe import OctaneProbe


def template_path(plugin_root: str) -> str:
    return os.path.join(plugin_root, "templates", "oidn_group.c4d")


def build(doc: Any, probe: OctaneProbe, selected: List[Any], plugin_root: str) -> dict:
    """Best-effort Tier-2 step. Never raises. Returns a status dict:

    {ok: bool, merged: bool, message: str, pending: int}
    """
    result = {"ok": False, "merged": False, "message": "", "pending": len(selected)}

    tpl = template_path(plugin_root)
    if os.path.exists(tpl):
        try:
            flags = getattr(c4d, "SCENEFILTER_MERGESCENE", 0) | getattr(c4d, "SCENEFILTER_OBJECTS", 0)
            merged = c4d.documents.MergeDocument(doc, tpl, flags, None)
            if merged:
                c4d.EventAdd()
                result.update(ok=True, merged=True,
                              message="Merged OIDN template — repoint each "
                                      "Render-Output-AOV source to its Light AOV.")
                return result
        except Exception as exc:  # noqa: BLE001
            print("[OLD/compositor] template merge failed: %s" % exc)

    # No template -> the auxiliaries exist; tell the user the one manual step.
    result["message"] = (
        "Render AOVs + Denoise Albedo/Normal are ready. The per-pass "
        "Open-Image-Denoiser wiring needs verified composite IDs — run the "
        "Inspector, or drop a hand-built group at templates/oidn_group.c4d "
        "to auto-merge it next time."
    )
    return result
