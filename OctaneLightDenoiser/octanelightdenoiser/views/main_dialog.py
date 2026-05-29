"""OctaneLightDenoiserDialog — the main panel (Manage / Build tabs).

Manage tab  : Light ID Manager — select lights (scene OM selection or in-panel
              checkboxes) and assign/group them by Light Pass ID. Lights sharing
              an ID = one group = one combined Light pass.
Build tab   : the pass picker — one row per light *group* (+ Sun/Env) + standard
              passes, with auto/manual output names, validation, and Build.

Native C4D GeDialog widgets: faithful structure/behaviour/state; C4D can't do
the mockup's gradients/green button so chrome uses the native dark theme.
"""
from __future__ import annotations

import os
from typing import Dict, List

import c4d
from c4d import gui

from ..c4d_compat import octane_ids as ids
from ..models.pass_item import PassItem, RowState
from ..services import naming, aov_builder, light_scanner, output_setup, compositor_builder
from ..services.octane_probe import OctaneProbe
from ..services.undo_helper import UndoSession

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OctaneLightDenoiserDialog(gui.GeDialog):
    def __init__(self) -> None:
        super().__init__()
        self._probe = OctaneProbe()
        self._phase = "empty"               # empty | ready
        self._tab = "manage"                # manage | build

        # manage-tab state
        self._scene_lights: List = []       # List[LightInfo]
        self._group_names: Dict[int, str] = {}
        self._mlight_selected: set = set()  # in-panel selected light keys
        self._use_scene = False
        self._target_id = 1

        # build-tab state
        self._items: List[PassItem] = []
        self._state: Dict[str, RowState] = {}
        self._collapsed: Dict[str, bool] = {
            cat: cat not in ids.DEFAULT_OPEN for cat, _ in ids.GROUPS
        }
        self._query = ""

        # rebuilt each layout
        self._row_index_map: Dict[int, str] = {}
        self._mlight_index_map: Dict[int, str] = {}
        self._group_index_map: Dict[int, int] = {}
        self._cat_index = {cat: i for i, (cat, _) in enumerate(ids.GROUPS)}

    # ================================================================ layout
    def CreateLayout(self) -> bool:
        self.SetTitle(ids.PLUGIN_NAME)
        self._build_header()
        self.AddSeparatorH(0)
        self._build_tabbar()
        if self.GroupBegin(ids.ID_BODY, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1):
            self._populate_body()
        self.GroupEnd()
        self._apply_values()
        self._refresh_chrome()
        return True

    def InitValues(self) -> bool:
        self._apply_values()
        self._refresh_chrome()
        return True

    def _build_header(self) -> None:
        if self.GroupBegin(ids.ID_HEADER_GROUP, c4d.BFH_SCALEFIT, cols=1):
            self.GroupBorderSpace(8, 8, 8, 6)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2):
                if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1):
                    self.AddStaticText(ids.ID_APPTITLE, c4d.BFH_SCALEFIT, name=ids.PLUGIN_NAME)
                    self.AddStaticText(ids.ID_APPSUB, c4d.BFH_SCALEFIT,
                                       name="Per-light OIDN · auto-named EXR passes")
                self.GroupEnd()
                self.AddStaticText(ids.ID_STATUS_PILL, c4d.BFH_RIGHT, name="")
            self.GroupEnd()
            self.AddButton(ids.ID_SCAN_BTN, c4d.BFH_SCALEFIT, name="Scan scene")
        self.GroupEnd()

    def _build_tabbar(self) -> None:
        if self.GroupBegin(ids.ID_TABBAR_GROUP, c4d.BFH_SCALEFIT, cols=2):
            self.GroupBorderSpace(8, 4, 8, 4)
            self.AddButton(ids.ID_TAB_MANAGE, c4d.BFH_SCALEFIT, name="Manage")
            self.AddButton(ids.ID_TAB_BUILD, c4d.BFH_SCALEFIT, name="Build")
        self.GroupEnd()
        self.AddSeparatorH(0)

    # ================================================================ body
    def _populate_body(self) -> None:
        if self._phase != "ready":
            self._body_empty()
        elif self._tab == "manage":
            self._body_manage()
        else:
            self._body_build()

    def _rebuild_body(self) -> None:
        self.LayoutFlushGroup(ids.ID_BODY)
        self._populate_body()
        self.LayoutChanged(ids.ID_BODY)
        self._apply_values()
        self._refresh_chrome()

    def _body_empty(self) -> None:
        if self._probe.available:
            msg = ("No scene scanned yet.\n\nScan to detect lights and the "
                   "standard render passes you can denoise.")
        else:
            msg = ("Octane not detected.\n\nThis plugin needs c4doctane 2024.1+. "
                   "Enable it, then re-open this panel.")
        self.AddStaticText(ids.ID_EMPTY_TEXT, c4d.BFH_SCALEFIT, name=msg)

    # ---------------------------------------------------------------- manage
    def _body_manage(self) -> None:
        if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1):
            self.GroupBorderSpace(8, 6, 8, 4)
            self.AddCheckbox(ids.ID_MGR_USESCENE, c4d.BFH_SCALEFIT, 0, 0,
                             name="Use scene selection (Object Manager)")
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=5):
                self.AddStaticText(0, c4d.BFH_LEFT, name="Assign →")
                self.AddComboBox(ids.ID_MGR_IDCOMBO, c4d.BFH_LEFT, 70, 0)
                for n in range(1, ids.MAX_LIGHT_IDS + 1):
                    self.AddChild(ids.ID_MGR_IDCOMBO, n, "ID %d" % n)
                self.AddButton(ids.ID_MGR_ASSIGN, c4d.BFH_LEFT, name="Assign")
                self.AddButton(ids.ID_MGR_NEW, c4d.BFH_LEFT, name="+ New")
                self.AddButton(ids.ID_MGR_CLEAR, c4d.BFH_LEFT, name="Clear")
            self.GroupEnd()
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=3):
                self.AddButton(ids.ID_MGR_SELALL, c4d.BFH_LEFT, name="Select all")
                self.AddButton(ids.ID_MGR_SELNONE, c4d.BFH_LEFT, name="Select none")
                self.AddButton(ids.ID_MGR_AUTO, c4d.BFH_RIGHT, name="Auto-assign all")
            self.GroupEnd()
            self.AddStaticText(ids.ID_MGR_STATUS, c4d.BFH_SCALEFIT, name="")
        self.GroupEnd()
        self.AddSeparatorH(0)

        if self.ScrollGroupBegin(ids.ID_MGR_SCROLL, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                                 c4d.SCROLLGROUP_VERT):
            if self.GroupBegin(ids.ID_MGR_LIST, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1):
                self.GroupBorderSpace(6, 6, 6, 6)
                self._build_manage_rows()
            self.GroupEnd()
        self.ScrollGroupEnd()

    def _build_manage_rows(self) -> None:
        self._mlight_index_map = {}
        self._group_index_map = {}

        self.AddStaticText(0, c4d.BFH_SCALEFIT, name="SCENE LIGHTS (%d)" % len(self._scene_lights))
        ri = 0
        for li in self._scene_lights:
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2):
                self.AddCheckbox(ids.mlight_id(ri, ids.MROW_OFF_CHK),
                                 c4d.BFH_SCALEFIT, 0, 0, name=li.name)
                tag = ("ID %d" % li.light_id) if isinstance(li.light_id, int) else "—  no ID"
                self.AddStaticText(ids.mlight_id(ri, ids.MROW_OFF_INFO),
                                   c4d.BFH_RIGHT, name=tag)
            self.GroupEnd()
            self._mlight_index_map[ri] = li.key
            ri += 1
        if not self._scene_lights:
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name="No Octane lights found in the scene.")

        self.AddSeparatorH(0)
        self.AddStaticText(0, c4d.BFH_SCALEFIT, name="GROUPS → PASSES")
        groups = light_scanner.group_by_id(self._scene_lights)
        gi = 0
        for gid in sorted(groups.keys()):
            members = groups[gid]
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=3):
                self.AddStaticText(0, c4d.BFH_LEFT, initw=46, name="ID %d" % gid)
                self.AddEditText(ids.group_row_id(gi, ids.GROW_OFF_NAME), c4d.BFH_SCALEFIT)
                self.AddStaticText(ids.group_row_id(gi, ids.GROW_OFF_INFO), c4d.BFH_RIGHT,
                                   name="%d → %s" % (len(members),
                                                     naming.auto_name(self._group_name_for(gid))))
            self.GroupEnd()
            self._group_index_map[gi] = gid
            gi += 1
        if not groups:
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name="No groups yet — assign lights to an ID above.")

        unassigned = [li.name for li in self._scene_lights if not isinstance(li.light_id, int)]
        if unassigned:
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name="⚠ Unassigned: " + ", ".join(unassigned))
        self.AddStaticText(0, c4d.BFH_SCALEFIT,
                           name="(Tip: lights sharing an ID = one combined pass. Name each group above.)")

    def _group_name_for(self, gid: int) -> str:
        # Neutral default ("Light <id>") — the user names groups themselves;
        # we don't borrow the light's object name (Key/Rim/Fill, etc.).
        name = self._group_names.get(gid, "")
        return name.strip() if name.strip() else "Light %d" % gid

    # ---------------------------------------------------------------- build
    def _body_build(self) -> None:
        if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=4):
            self.GroupBorderSpace(8, 4, 8, 4)
            self.AddButton(ids.ID_SEL_ALL, c4d.BFH_LEFT, name="All")
            self.AddButton(ids.ID_SEL_NONE, c4d.BFH_LEFT, name="None")
            self.AddButton(ids.ID_AUTONAME_ALL, c4d.BFH_LEFT, name="Auto-name")
            self.AddEditText(ids.ID_SEARCH, c4d.BFH_SCALEFIT)
        self.GroupEnd()
        self.AddSeparatorH(0)

        if self.ScrollGroupBegin(ids.ID_LIST_SCROLL, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                                 c4d.SCROLLGROUP_VERT):
            if self.GroupBegin(ids.ID_LIST_GROUP, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1):
                self.GroupBorderSpace(6, 6, 6, 6)
                self._build_rows()
            self.GroupEnd()
        self.ScrollGroupEnd()
        self.AddSeparatorH(0)

        if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1):
            self.GroupBorderSpace(8, 6, 8, 8)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2):
                self.AddButton(ids.ID_SETUP_EXR, c4d.BFH_SCALEFIT, name="Setup EXR")
                self.AddButton(ids.ID_INSPECTOR, c4d.BFH_SCALEFIT, name="Inspector")
            self.GroupEnd()
            self.AddButton(ids.ID_BUILD, c4d.BFH_SCALEFIT, name="Build Denoise")
            self.AddStaticText(ids.ID_FOOT_STATUS, c4d.BFH_SCALEFIT, name="")
        self.GroupEnd()

    def _build_rows(self) -> None:
        self._row_index_map = {}
        self._recompute_validation()

        q = self._query.strip().lower()
        ri = 0
        for cat, label in ids.GROUPS:
            rows = [it for it in self._items if it.cat == cat and self._match(it, q)]
            if not rows:
                continue
            sel = sum(1 for it in rows if self._state[it.id].selected)
            # Force-expand a category that hides a selected row with an error,
            # so a Build-blocking name issue is always visible to fix.
            has_err = any(self._state[it.id].selected and self._state[it.id].error
                          for it in rows)
            collapsed = self._collapsed.get(cat, False) and not q and not has_err
            tri = "▸" if collapsed else "▾"
            self.AddButton(ids.group_head_id(self._cat_index[cat]), c4d.BFH_SCALEFIT,
                           name="%s  %s    %d  ·  %d sel" % (tri, label.upper(), len(rows), sel))
            if collapsed:
                continue
            for it in rows:
                self._build_row(ri, it)
                ri += 1

    def _build_row(self, ri: int, it: PassItem) -> None:
        st = self._state[it.id]
        if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1):
            self.GroupBorder(c4d.BORDER_GROUP_IN)
            self.GroupBorderSpace(6, 3, 6, 3)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2):
                self.AddCheckbox(ids.row_widget_id(ri, ids.ROW_OFF_CHK),
                                 c4d.BFH_SCALEFIT, 0, 0, name=it.source)
                self.AddStaticText(ids.row_widget_id(ri, ids.ROW_OFF_INFO),
                                   c4d.BFH_RIGHT, name=self._info_text(it, st))
            self.GroupEnd()
            if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=3):
                self.AddStaticText(0, c4d.BFH_LEFT, name="→")
                self.AddEditText(ids.row_widget_id(ri, ids.ROW_OFF_NAME), c4d.BFH_SCALEFIT)
                action = self._action_label(st)
                if action:
                    self.AddButton(ids.row_widget_id(ri, ids.ROW_OFF_ACTION),
                                   c4d.BFH_RIGHT, name=action)
                else:
                    self.AddStaticText(ids.row_widget_id(ri, ids.ROW_OFF_ACTION),
                                       c4d.BFH_RIGHT, name="auto")
            self.GroupEnd()
            if st.error and st.selected:
                self.AddStaticText(ids.row_widget_id(ri, ids.ROW_OFF_ERR),
                                   c4d.BFH_SCALEFIT, name="⚠ " + st.error)
        self.GroupEnd()
        self._row_index_map[ri] = it.id

    @staticmethod
    def _info_text(it: PassItem, st: RowState) -> str:
        bits = []
        if it.cat == "LIGHT":
            if it.light_id in (ids.LIGHT_SUN, ids.LIGHT_ENV):
                bits.append(str(it.light_id))
            elif isinstance(it.light_id, int):
                bits.append("ID %d" % it.light_id)
        if it.note:
            bits.append(it.note)
        if it.required:
            bits.append("aux")
        if it.already:
            bits.append("exists")
        if st.built:
            bits.append("✓ built")
        bits.append("[set]" if not st.auto else "[auto]")
        return "  ".join(bits)

    @staticmethod
    def _action_label(st: RowState) -> str:
        if st.error and st.fixable:
            return "Fix"
        if not st.auto:
            return "Revert"
        return ""

    def _match(self, it: PassItem, q: str) -> bool:
        if not q:
            return True
        if q in it.source.lower():
            return True
        st = self._state.get(it.id)
        return bool(st and q in st.name.lower())

    # ================================================================ values
    def _apply_values(self) -> None:
        if self._phase != "ready":
            return
        if self._tab == "manage":
            self._apply_manage_values()
        else:
            self._apply_build_values()

    def _apply_manage_values(self) -> None:
        self.SetInt32(ids.ID_MGR_IDCOMBO, self._target_id)
        self.SetBool(ids.ID_MGR_USESCENE, self._use_scene)
        scene_sel = (light_scanner.selected_in_scene(self._doc(), self._scene_lights)
                     if self._use_scene else set())
        for ri, key in self._mlight_index_map.items():
            val = (key in scene_sel) if self._use_scene else (key in self._mlight_selected)
            self.SetBool(ids.mlight_id(ri, ids.MROW_OFF_CHK), val)
            self.Enable(ids.mlight_id(ri, ids.MROW_OFF_CHK), not self._use_scene)
        for ri, gid in self._group_index_map.items():
            self.SetString(ids.group_row_id(ri, ids.GROW_OFF_NAME), self._group_name_for(gid))
        # In scene-selection mode the list checkboxes are read-only, so the
        # in-panel Select all/none don't apply — disable them to avoid dead clicks.
        self.Enable(ids.ID_MGR_SELALL, not self._use_scene)
        self.Enable(ids.ID_MGR_SELNONE, not self._use_scene)

    def _apply_build_values(self) -> None:
        for ri, pid in self._row_index_map.items():
            it = next((x for x in self._items if x.id == pid), None)
            st = self._state.get(pid)
            if it is None or st is None:
                continue
            self.SetBool(ids.row_widget_id(ri, ids.ROW_OFF_CHK), st.selected)
            self.SetString(ids.row_widget_id(ri, ids.ROW_OFF_NAME), st.name)
            if it.disabled:
                self.Enable(ids.row_widget_id(ri, ids.ROW_OFF_CHK), False)
                self.Enable(ids.row_widget_id(ri, ids.ROW_OFF_NAME), False)

    # ================================================================ validation
    def _recompute_validation(self) -> None:
        counts: Dict[str, int] = {}
        for it in self._items:
            st = self._state.get(it.id)
            if st and st.selected:
                counts[st.name] = counts.get(st.name, 0) + 1
        for it in self._items:
            st = self._state.get(it.id)
            if not st:
                continue
            if st.selected:
                st.error, st.fixable = naming.validate(st.name, name_counts=counts)
            else:
                st.error, st.fixable = None, False

    def _counts(self):
        sel = sum(1 for st in self._state.values() if st.selected)
        err = sum(1 for st in self._state.values() if st.selected and st.error)
        return sel, err

    # ================================================================ chrome
    def _refresh_chrome(self) -> None:
        ready = self._phase == "ready"
        if self._probe.available:
            v = self._probe.version
            pill = ("● %s" % v) if "ctane" in v.lower() else ("● Octane %s" % v)
        else:
            pill = "● Not found"
        self.SetString(ids.ID_STATUS_PILL, pill)
        self.SetString(ids.ID_SCAN_BTN, "Re-scan" if ready else "Scan scene")
        self.Enable(ids.ID_SCAN_BTN, self._probe.available)
        self.SetString(ids.ID_TAB_MANAGE, "● Manage" if self._tab == "manage" else "Manage")
        self.SetString(ids.ID_TAB_BUILD, "● Build" if self._tab == "build" else "Build")
        self.Enable(ids.ID_TAB_MANAGE, ready)
        self.Enable(ids.ID_TAB_BUILD, ready)

        if ready and self._tab == "build":
            sel, err = self._counts()
            self.Enable(ids.ID_BUILD, sel > 0 and err == 0)
            if err > 0:
                self.SetString(ids.ID_FOOT_STATUS, "⚠ %d name%s need fixing" % (err, "s" if err > 1 else ""))
            elif sel == 0:
                self.SetString(ids.ID_FOOT_STATUS, "Select at least one pass to build")
            else:
                self.SetString(ids.ID_FOOT_STATUS, "✓ %d pass%s ready" % (sel, "es" if sel > 1 else ""))
        elif ready and self._tab == "manage":
            self._update_manage_status()

    def _update_manage_status(self) -> None:
        if self._use_scene:
            n = len(light_scanner.selected_in_scene(self._doc(), self._scene_lights))
            src = "scene"
        else:
            n = len(self._mlight_selected)
            src = "list"
        self.SetString(ids.ID_MGR_STATUS,
                       "Selected: %d light%s (%s)" % (n, "s" if n != 1 else "", src))

    # ================================================================ commands
    def Command(self, cid: int, msg: c4d.BaseContainer) -> bool:
        if cid == ids.ID_SCAN_BTN:
            self._do_scan()
        elif cid == ids.ID_TAB_MANAGE:
            self._switch_tab("manage")
        elif cid == ids.ID_TAB_BUILD:
            self._switch_tab("build")
        # ----- manage controls -----
        elif cid == ids.ID_MGR_USESCENE:
            self._use_scene = self.GetBool(cid)
            self._rebuild_body()
        elif cid == ids.ID_MGR_IDCOMBO:
            self._target_id = self.GetInt32(cid) or 1
        elif cid == ids.ID_MGR_ASSIGN:
            self._assign()
        elif cid == ids.ID_MGR_NEW:
            self._new_group()
        elif cid == ids.ID_MGR_CLEAR:
            self._clear()
        elif cid == ids.ID_MGR_AUTO:
            self._auto_assign()
        elif cid == ids.ID_MGR_SELALL:
            self._mlight_select_all(True)
        elif cid == ids.ID_MGR_SELNONE:
            self._mlight_select_all(False)
        # ----- build controls -----
        elif cid == ids.ID_SEL_ALL:
            self._select_all(True)
        elif cid == ids.ID_SEL_NONE:
            self._select_all(False)
        elif cid == ids.ID_AUTONAME_ALL:
            self._auto_name_all()
        elif cid == ids.ID_SEARCH:
            self._query = self.GetString(ids.ID_SEARCH) or ""
            self._rebuild_list()
        elif cid == ids.ID_SETUP_EXR:
            self.SetString(ids.ID_FOOT_STATUS, output_setup.setup_exr(self._doc(), self._probe))
        elif cid == ids.ID_INSPECTOR:
            gui.MessageDialog(self._probe.inspect(self._doc()))
        elif cid == ids.ID_BUILD:
            self._do_build()
        # ----- dynamic -----
        elif ids.ID_GROUP_HEAD_BASE <= cid < ids.ID_GROUP_HEAD_BASE + 100:
            self._toggle_group(cid - ids.ID_GROUP_HEAD_BASE)
        elif ids.is_row_widget(cid):
            self._on_row_widget(cid)
        elif ids.is_mlight(cid):
            self._on_mlight(cid)
        elif ids.is_group_row(cid):
            self._on_group_row(cid)
        return True

    @staticmethod
    def _doc():
        return c4d.documents.GetActiveDocument()

    def _switch_tab(self, tab: str) -> None:
        if tab != self._tab and self._phase == "ready":
            self._tab = tab
            self._rebuild_body()

    # ----- build-tab live updates -----
    def _rebuild_list(self) -> None:
        if self._tab != "build" or self._phase != "ready":
            return
        self.LayoutFlushGroup(ids.ID_LIST_GROUP)
        self._build_rows()
        self.LayoutChanged(ids.ID_LIST_GROUP)
        self._apply_build_values()
        self._refresh_chrome()

    def _on_row_widget(self, cid: int) -> None:
        ri, off = ids.decode_row_widget(cid)
        pid = self._row_index_map.get(ri)
        if pid is None:
            return
        it = next((x for x in self._items if x.id == pid), None)
        st = self._state.get(pid)
        if it is None or st is None:
            return
        if off == ids.ROW_OFF_CHK:
            st.selected = self.GetBool(cid)
            self._rebuild_list()
        elif off == ids.ROW_OFF_NAME:
            st.name = self.GetString(cid) or ""
            st.auto = (st.name == naming.auto_name(it.source))
            self._rebuild_list()
        elif off == ids.ROW_OFF_ACTION:
            if st.error and st.fixable:
                st.name = naming.sanitize(st.name)
            elif not st.auto:
                st.name = naming.auto_name(it.source)
                st.auto = True
            self._rebuild_list()

    def _toggle_group(self, group_index: int) -> None:
        cat = next((c for c, i in self._cat_index.items() if i == group_index), None)
        if cat is not None:
            self._collapsed[cat] = not self._collapsed.get(cat, False)
            self._rebuild_list()

    def _select_all(self, value: bool) -> None:
        for it in self._items:
            if not it.disabled:
                self._state[it.id].selected = value
        self._rebuild_list()

    def _auto_name_all(self) -> None:
        for it in self._items:
            st = self._state[it.id]
            st.name = naming.auto_name(it.source)
            st.auto = True
        self._rebuild_list()

    # ----- manage-tab live updates -----
    def _rebuild_manage(self) -> None:
        if self._tab != "manage" or self._phase != "ready":
            return
        self.LayoutFlushGroup(ids.ID_MGR_LIST)
        self._build_manage_rows()
        self.LayoutChanged(ids.ID_MGR_LIST)
        self._apply_manage_values()
        self._refresh_chrome()

    def _effective_lights(self) -> List:
        if self._use_scene:
            keys = light_scanner.selected_in_scene(self._doc(), self._scene_lights)
        else:
            keys = self._mlight_selected
        return [li for li in self._scene_lights if li.key in keys]

    def _refresh_items(self, reset_state: bool = False) -> None:
        self._items = light_scanner.build_catalog(
            self._doc(), self._probe, self._scene_lights, self._group_names)
        old = {} if reset_state else self._state
        new: Dict[str, RowState] = {}
        for it in self._items:
            if it.id in old:
                st = old[it.id]
            else:
                default_sel = (it.cat == "LIGHT" and isinstance(it.light_id, int)) or it.required
                st = RowState(selected=default_sel, name=naming.auto_name(it.source), auto=True)
            if st.auto:                       # keep auto name in sync with source/group rename
                st.name = naming.auto_name(it.source)
            new[it.id] = st
        self._state = new

    def _on_mlight(self, cid: int) -> None:
        ri, off = ids.decode_mlight(cid)
        key = self._mlight_index_map.get(ri)
        if key is None or off != ids.MROW_OFF_CHK:
            return
        if self.GetBool(cid):
            self._mlight_selected.add(key)
        else:
            self._mlight_selected.discard(key)
        self._update_manage_status()

    def _on_group_row(self, cid: int) -> None:
        ri, off = ids.decode_group_row(cid)
        gid = self._group_index_map.get(ri)
        if gid is None or off != ids.GROW_OFF_NAME:
            return
        self._group_names[gid] = self.GetString(cid) or ""
        self._refresh_items()
        self._rebuild_manage()

    def _assign(self) -> None:
        lights = self._effective_lights()
        if not lights:
            gui.MessageDialog("Select one or more lights first (scene or list).")
            return
        n = light_scanner.assign_id_to(self._doc(), self._probe, lights, self._target_id)
        self._refresh_items()
        self._rebuild_manage()
        self.SetString(ids.ID_MGR_STATUS,
                       "Assigned ID %d to %d light%s" % (self._target_id, n, "s" if n != 1 else ""))

    def _new_group(self) -> None:
        nid = light_scanner.next_free_id(self._scene_lights)
        if nid is None:
            gui.MessageDialog("All 8 Light IDs are in use.")
            return
        self._target_id = nid
        self._assign()

    def _clear(self) -> None:
        lights = self._effective_lights()
        if not lights:
            gui.MessageDialog("Select one or more lights first.")
            return
        n = light_scanner.clear_ids(self._doc(), self._probe, lights)
        self._refresh_items()
        self._rebuild_manage()
        self.SetString(ids.ID_MGR_STATUS, "Cleared ID on %d light%s" % (n, "s" if n != 1 else ""))

    def _auto_assign(self) -> None:
        n = light_scanner.auto_assign_all(self._doc(), self._probe, self._scene_lights)
        self._refresh_items()
        self._rebuild_manage()
        self.SetString(ids.ID_MGR_STATUS, "Auto-assigned %d light%s" % (n, "s" if n != 1 else ""))

    def _mlight_select_all(self, value: bool) -> None:
        if self._use_scene:
            return
        if value:
            self._mlight_selected = {li.key for li in self._scene_lights}
        else:
            self._mlight_selected = set()
        self._rebuild_manage()

    # ================================================================ scan / build
    def _do_scan(self) -> None:
        if not self._probe.available:
            self._phase = "empty"
            self._rebuild_body()
            gui.MessageDialog(self._probe.diagnostics())   # tell the user WHY
            return
        self._scene_lights = light_scanner.get_scene_lights(self._doc(), self._probe)
        self._group_names = {}
        self._mlight_selected = set()
        self._refresh_items(reset_state=True)
        self._phase = "ready"
        self._rebuild_body()

    def _do_build(self) -> None:
        self._recompute_validation()
        sel, err = self._counts()
        if sel == 0 or err > 0:
            gui.MessageDialog("Fix name issues and select at least one pass first.")
            return
        doc = self._doc()
        vp = self._probe.find_videopost(doc)
        if vp is None:
            gui.MessageDialog("No Octane VideoPost found.\nSet the renderer to Octane "
                              "in Render Settings, then Re-scan.")
            return

        used: set = set()
        built, skipped = 0, 0
        selected = [it for it in self._items if self._state[it.id].selected]
        with UndoSession(doc, label="Build Denoise Passes") as undo:
            undo.record_change(vp)
            for it in selected:
                st = self._state[it.id]
                final = naming.resolve_name(None if st.auto else st.name, it.source, used)
                st.name = final
                st.auto = (final == naming.auto_name(it.source))
                if it.aov_type is None:
                    skipped += 1
                    continue
                shader = aov_builder.add_aov(vp, self._probe, it.aov_type, final,
                                             light_id=it.light_id, undo=undo)
                if shader is not None:
                    built += 1
                    st.built = True
                else:
                    skipped += 1
        c4d.EventAdd()

        comp = compositor_builder.build(doc, self._probe, selected, _PLUGIN_ROOT)
        self.SetString(ids.ID_FOOT_STATUS, "✓ Built %d · %d skipped" % (built, skipped))
        self._rebuild_list()
        msg = ["Built %d Render AOV%s." % (built, "s" if built != 1 else "")]
        if skipped:
            msg.append("%d pass(es) skipped (type not verified on this build)." % skipped)
        msg += ["", comp.get("message", "")]
        gui.MessageDialog("\n".join(msg))
