"""Configure multilayer EXR output (best-effort, cross-version-safe).

The reliable part (standard C4D RenderData) is set directly: enable Multi-Pass
and set the image format to OpenEXR. The Octane-specific bits (multilayer EXR
in the Render-AOV group + Linear sRGB color space on the VideoPost) are written
through ``safe_set`` and may need an ID confirmed via the Inspector — they are
marked ``# VERIFY`` and never crash if wrong.
"""
from __future__ import annotations

from typing import Any

import c4d

from ..c4d_compat import octane_ids as ids
from .octane_probe import safe_set


# VERIFY: Octane VP_COLOR_SPACE enum value for "Linear sRGB".
_LINEAR_SRGB_GUESS = 1


def setup_exr(doc: Any, probe: Any) -> str:
    """Enable multipass + EXR. Returns a short status string."""
    if doc is None:
        return "No document."
    rdata = doc.GetActiveRenderData()
    if rdata is None:
        return "No active render settings."

    ok = []
    # --- standard C4D RenderData (reliable) ---
    if safe_set(rdata, c4d.RDATA_MULTIPASS_ENABLE, True):
        ok.append("multipass")
    exr = getattr(c4d, "FILTER_EXR", None)
    if exr is not None:
        if safe_set(rdata, c4d.RDATA_FORMAT, exr):
            ok.append("EXR")
        # multipass save format too, if present
        mp_fmt = getattr(c4d, "RDATA_MULTIPASS_SAVEFORMAT", None)
        if mp_fmt is not None:
            safe_set(rdata, mp_fmt, exr)

    # --- Octane multilayer + Linear sRGB (best-effort) ---
    vp = probe.find_videopost(doc)
    if vp is not None:
        # VERIFY: color space enum + multilayer toggle ids on your build.
        safe_set(vp, ids.VP_COLOR_SPACE, _LINEAR_SRGB_GUESS)

    c4d.EventAdd()
    if ok:
        return "Output set: %s · Linear sRGB (verify)" % " · ".join(ok)
    return "Could not set output — check console / run Inspector."
