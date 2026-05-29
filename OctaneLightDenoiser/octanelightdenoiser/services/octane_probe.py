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
        self._vp_plugin: Any = None
        self._version: str = "unknown"
        self._passid_param = None        # cached resolved Light-tag pass-id param
        self._detect()

    # ----- discovery -----
    def _detect(self) -> None:
        # (1) optional Python module — only used for symbol resolution/version.
        #     Octane may NOT expose an importable `c4doctane`; that's fine.
        try:
            import c4doctane  # type: ignore
            self._mod = c4doctane
        except Exception:
            self._mod = getattr(getattr(c4d, "modules", None), "octane", None)

        # (2) plugin registry — the RELIABLE "is Octane installed" test. The
        #     plugin runs off numeric IDs, so availability hinges on this, not
        #     on the module import.
        try:
            fp = c4d.plugins.FindPlugin(ids.OCTANE_VIDEO_POST, c4d.PLUGINTYPE_VIDEOPOST)
            if fp is None:
                fp = c4d.plugins.FindPlugin(ids.OCTANE_VIDEO_POST)
            self._vp_plugin = fp
        except Exception:
            self._vp_plugin = None

        self._version = self._detect_version()

    def _detect_version(self) -> str:
        if self._vp_plugin is not None:
            try:
                nm = self._vp_plugin.GetName()
                if nm:
                    return nm
            except Exception:
                pass
        if self._mod is not None:
            for attr in ("__version__", "version", "OCTANE_VERSION", "VERSION"):
                v = getattr(self._mod, attr, None)
                if v:
                    return str(v)
        return "installed" if self.available else "unknown"

    def _has_symbol(self) -> bool:
        """Octane injects symbols into the c4d namespace; a present one => installed."""
        return any(isinstance(getattr(c4d, n, None), int)
                   for n in ("RNDAOV_LIGHT_ID", "VPocta"))

    @property
    def available(self) -> bool:
        return self._vp_plugin is not None or self._mod is not None or self._has_symbol()

    @property
    def version(self) -> str:
        return self._version

    def diagnostics(self) -> str:
        """Human-readable detection report (shown if Scan finds no Octane)."""
        try:
            fp = c4d.plugins.FindPlugin(ids.OCTANE_VIDEO_POST, c4d.PLUGINTYPE_VIDEOPOST)
        except Exception:
            fp = None
        lines = [
            "Octane detection report:",
            "  c4doctane module : %s" % ("imported" if self._mod is not None else "not importable"),
            "  VideoPost plugin %s : %s" % (
                ids.OCTANE_VIDEO_POST,
                ("found (%s)" % fp.GetName()) if fp is not None else "NOT registered"),
            "  c4d Octane symbols : %s" % ("present" if self._has_symbol() else "absent"),
            "  => available : %s   version : %s" % (self.available, self.version),
        ]
        if not self.available:
            lines += [
                "",
                "Octane was not detected in this Cinema 4D.",
                "Check that the Octane (c4doctane) plugin is installed AND enabled,",
                "set the renderer to Octane in Render Settings, then re-open the panel.",
            ]
        return "\n".join(lines)

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
            self._dump_shaders(vp)

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

    def _dump_shaders(self, vp: Any) -> None:
        """Walk EVERY shader on the VideoPost — reveals composite / Output-AOV
        and Open-Image-Denoiser nodes (the Tier-2 data we're missing).
        Render-AOV nodes get a one-liner; any OTHER node type gets a full param
        dump (that's the structure we need to wire OIDN automatically).
        """
        print("\n--- ALL shaders on VideoPost (Tier 2: composite / OIDN nodes) ---")
        rp = self.renderpass_type()

        def walk(sh: Any, depth: int = 0) -> None:
            pad = "  " * depth
            while sh is not None:
                t = sh.GetType()
                print("%s* type=%s name=%r" % (pad, t, sh.GetName()))
                if t != rp:                       # unknown node -> full param dump
                    bc = sh.GetDataInstance()
                    if bc is not None:
                        for cid, val in bc:
                            try:
                                print("%s    [%s]=%r" % (pad, cid, val))
                            except Exception:
                                pass
                walk(sh.GetDown(), depth + 1)
                sh = sh.GetNext()

        try:
            walk(vp.GetFirstShader())
        except Exception as exc:  # noqa: BLE001
            print("  <shader walk failed: %s>" % exc)
