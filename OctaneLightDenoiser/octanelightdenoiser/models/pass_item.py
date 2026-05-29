"""Data models.

`PassItem`  = one buildable pass in the Build tab (a light *group*, a standard
              pass, or an existing AOV).
`RowState`  = per-row Build-tab UI state (selection, edited name, validation).
`LightInfo` = one scene light in the Manage tab (object + Octane tag + its
              current Light Pass ID). Lights sharing a Light ID form a group,
              and each group renders as ONE Light AOV / pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PassItem:
    id: str                       # stable row key (e.g. "G1" group, "S3" standard)
    cat: str                      # group key: LIGHT / AUXILIARY / BEAUTY / ...
    source: str                   # source/group name shown on line 1
    light_id: Optional[Any] = None   # int 1..8 (group), "Sun", "Env", or None
    already: bool = False
    required: bool = False
    aov_type: Optional[int] = None
    note: Optional[str] = None    # e.g. "2 lights"

    @property
    def is_light(self) -> bool:
        return self.cat == "LIGHT"

    @property
    def is_scene_light(self) -> bool:
        return self.cat == "LIGHT" and self.light_id not in (None, "Sun", "Env")

    @property
    def disabled(self) -> bool:
        return self.cat == "LIGHT" and self.light_id is None


@dataclass
class RowState:
    selected: bool = False
    name: str = ""
    auto: bool = True
    error: Optional[str] = None
    fixable: bool = False
    built: bool = False


@dataclass
class LightInfo:
    key: str                      # stable per-scan key (e.g. "ML3")
    obj: Any                      # the C4D BaseObject carrying the light
    tag: Any                      # the Octane Light tag
    name: str
    light_id: Optional[int] = None   # 1..8, or None (unassigned)
