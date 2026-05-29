"""Octane discovery, cross-version symbol resolution, and the built-in Inspector.

There is no official Octane Python SDK, so every numeric ID is community-derived.
This module is the single place that touches Octane's quirks:

  * loads ``c4doctane`` (or the legacy module) and reports a version string,
  * resolves handles through ``getattr(c4doctane, NAME, fallback_id)``,
  * ``safe_set`` / ``safe_get`` never raise (log + continue) so a bad ID can
    never crash the plugin,
  * finds the Octane VideoPost on the active RenderData,
  * ``inspect(doc)`` dumps the *real* IDs from the current scene to the console
    so you can confirm / fix anything marked ``# VERIFY`` in octane_ids.py.
"""
from __future__ import annotations

from typing import Any, Optional

import c4d

from ..c4d_compat import octane_ids as ids


# ----------------------------------------------------------------- safe IO
def safe_set(op: Any, pid: int, value: Any) -> bool:
    """Write op[pid] = value; log and return False on failure (never raises)."""
    if op is None or pid is None:
        return False
    try:
        op[pid] = value
        return True
    except Exception as exc:  # noqa: BLE001 - cross-version resilience
        print("[OLD/Octane] write [%s] failed: %s" % (pid, exc))
        return False


def safe_get(op: Any, pid: int, default: Any = None) -> Any:
    if op is None or pid is None:
        return default
    try:
        return op[pid]
    except Exception:
        return default


def iter_objects(op: Any):
    """Depth-first walk over an object hierarchy starting at `op`."""
    while op:
        yield op
        child = op.GetDown()
        if child:
            for c in iter_objects(child):
                yield c
        op = op.GetNext()


class OctaneProbe:
    """Detects Octane and resolves its IDs defensively."""

    def __init__(self) -> None:
        self._mod: Any = None
        self._version: str = "unknown"
        self._passid_param = None        # cached resolved Light-tag pass-id param
        self._load()
        if self._mod is not None:
            self._detect_version()

    # ----- discovery -----
    def _load(self) -> None:
        try:
            import c4doctane  # type: ignore
            self._mod = c4doctane
            return
        except Exception:
            pass
        legacy = getattr(getattr(c4d, "modules", None), "octane", None)
        if legacy is not None:
            self._mod = legacy

    def _detect_version(self) -> None:
        for attr in ("__version__", "version", "OCTANE_VERSION", "VERSION"):
            v = getattr(self._mod, attr, None)
            if v:
                self._version = str(v)
                return
        self._version = "detected"

    @property
    def available(self) -> bool:
        return self._mod is not None

    @property
    def version(self) -> str:
        return self._version

    # ----- symbol resolution -----
    def resolve(self, names: tuple, fallback: int) -> int:
        """First int found among c4doctane.<name> / c4d.<name>, else fallback.

        Octane injects many of its symbols into the `c4d` namespace, so both
        namespaces are checked before giving up to the numeric fallback.
        """
        for ns in (self._mod, c4d):
            if ns is None:
                continue
            for n in names:
                v = getattr(ns, n, None)
                if isinstance(v, int):
                    return v
        return fallback

    def videopost_type(self) -> int:
        return self.resolve(ids.SYMBOL_VIDEO_POST, ids.OCTANE_VIDEO_POST)

    def renderpass_type(self) -> int:
        return self.resolve(ids.SYMBOL_RENDERPASS, ids.OCTANE_RENDERPASS_AOV)

    def lighttag_type(self) -> int:
        return self.resolve(ids.SYMBOL_LIGHT_TAG, ids.OCTANE_LIGHT_TAG)

    # ----- scene helpers -----
    def find_videopost(self, doc: Any) -> Optional[Any]:
        if doc is None:
            return None
        rdata = doc.GetActiveRenderData()
        if rdata is None:
            return None
        want = self.videopost_type()
        vp = rdata.GetFirstVideoPost()
        while vp:
            if vp.GetType() == want:
                return vp
            vp = vp.GetNext()
        return None

    def lighttag_passid_param(self) -> int:
        """Resolved param id for the Light tag's 'Light Pass ID' (0 if unknown).

        Resolved by NAME (c4doctane / c4d), cached. 0 means "use numeric guesses".
        """
        if self._passid_param is None:
            self._passid_param = self.resolve(ids.LIGHTTAG_PASS_ID_SYMBOLS, 0)
        return self._passid_param

    def _passid_candidates(self):
        pid = self.lighttag_passid_param()
        return ([pid] if pid else []) + list(ids.LIGHTTAG_PASS_ID_CANDIDATES)

    def read_light_pass_id(self, tag: Any) -> Optional[int]:
        """Best-effort read of the Light Pass ID from an Octane Light tag.

        Tries the name-resolved param first, then numeric candidates; accepts
        the first int in 1..20. Returns None (-> "no ID") if nothing reads.
        """
        if tag is None:
            return None
        for pid in self._passid_candidates():
            v = safe_get(tag, pid, None)
            if isinstance(v, int) and 1 <= v <= 20:
                return v
        return None

    def passid_write_param(self, tag: Any) -> int:
        """Best param id to WRITE the Light Pass ID onto a tag."""
        pid = self.lighttag_passid_param()
        if pid:
            return pid
        for p in ids.LIGHTTAG_PASS_ID_CANDIDATES:
            if isinstance(safe_get(tag, p, None), int):
                return p
        return ids.LIGHTTAG_PASS_ID_CANDIDATES[0]

    # ----- the built-in inspector (Stage-1) -----
    def inspect(self, doc: Any) -> str:
        """Dump real IDs to the console. Returns a short status string."""
        print("\n" + "=" * 60)
        print(" Octane Light Denoiser — Inspector")
        print("=" * 60)
        print(" c4doctane available: %s   version: %s" % (self.available, self.version))
        if not self.available:
            return "Octane module not found — see console."

        vp = self.find_videopost(doc)
        if vp is None:
            print(" !! No Octane VideoPost on active RenderData "
                  "(open Render Settings, set renderer to Octane).")
        else:
            print(" Octane VideoPost found (type %s)" % vp.GetType())
            cnt = safe_get(vp, ids.SET_RENDERAOV_IN_CNT, None)
            print(" Render AOV count [%s] = %s" % (ids.SET_RENDERAOV_IN_CNT, cnt))
            for i in range(cnt or 0):
                aov = safe_get(vp, ids.SET_RENDERAOV_INPUT_0 + i, None)
                if aov is not None:
                    print("   slot %d: name=%r type=%s enabled=%s lightId=%s" % (
                        i,
                        safe_get(aov, ids.RNDAOV_NAME),
                        safe_get(aov, ids.RNDAOV_TYPE),
                        safe_get(aov, ids.RNDAOV_ENABLED),
                        safe_get(aov, ids.RNDAOV_LIGHT_ID),
                    ))
            self._dump_bc(vp, "VideoPost FULL (look for composite/Output-AOV base + name param)")

        print(" Light-tag pass-id param resolved by name = %s  "
              "(0 = none; numeric guesses tried = %s)"
              % (self.lighttag_passid_param(), ids.LIGHTTAG_PASS_ID_CANDIDATES))

        # Light tag of the active object
        obj = doc.GetActiveObject() if doc else None
        if obj is not None:
            want = self.lighttag_type()
            tag = obj.GetFirstTag()
            found = False
            while tag:
                if tag.GetType() == want:
                    found = True
                    self._dump_bc(tag, "Octane Light Tag (look for 'Light Pass ID')")
                tag = tag.GetNext()
            if not found:
                print(" (active object has no Octane Light tag — select a light)")
        else:
            print(" (select an object with an Octane Light tag to dump Pass-ID param)")

        print("=" * 60 + "\n")
        return "Inspector dump written to the console (Script/Console)."

    @staticmethod
    def _dump_bc(node: Any, label: str) -> None:
        if node is None:
            print("--- %s: <None> ---" % label)
            return
        print("\n--- %s: '%s' (type %s) ---" % (label, node.GetName(), node.GetType()))
        bc = node.GetDataInstance()
        if bc is None:
            print("  <no container>")
            return
        try:
            for cid, val in bc:
                try:
                    print("  [%s] = %r" % (cid, val))
                except Exception:
                    print("  [%s] = <unprintable>" % cid)
        except Exception as exc:  # noqa: BLE001
            print("  <iteration failed: %s>" % exc)
