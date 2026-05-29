"""Undo grouping for batched scene mutations.

C4D records every individual change. Wrapping a batch of mutations in
StartUndo()/EndUndo() collapses them into a single undoable step so a "Build"
or "Auto-assign IDs" is one Ctrl+Z, not dozens.
"""
from __future__ import annotations

from typing import Any

import c4d


class UndoSession:
    """Context manager that opens one undo group for a batch of mutations.

    Use AddUndo *before* changing each object (UNDOTYPE_CHANGE) or right after
    inserting a new one (UNDOTYPE_NEW). Call ``record_new`` / ``record_change``
    inside the ``with`` block.
    """

    def __init__(self, doc: Any, *, label: str = "Octane Light Denoiser") -> None:
        self._doc = doc
        self._label = label
        self._opened = False

    def __enter__(self) -> "UndoSession":
        if self._doc is not None:
            self._doc.StartUndo()
            self._opened = True
        return self

    def record_change(self, op: Any) -> None:
        if self._opened and op is not None:
            try:
                self._doc.AddUndo(c4d.UNDOTYPE_CHANGE, op)
            except Exception as exc:  # noqa: BLE001
                print("[OLD/undo] AddUndo CHANGE failed: %s" % exc)

    def record_new(self, op: Any) -> None:
        if self._opened and op is not None:
            try:
                self._doc.AddUndo(c4d.UNDOTYPE_NEW, op)
            except Exception as exc:  # noqa: BLE001
                print("[OLD/undo] AddUndo NEW failed: %s" % exc)

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._opened and self._doc is not None:
            self._doc.EndUndo()
        self._opened = False
