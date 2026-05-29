"""Octane Light Denoiser — pass picker + Build Denoise  (ZHiCK Tool).

This .pyp also injects the shared "ZHiCK Tool" submenu that groups both
commands (this one + the Light ID Manager). The Light ID Manager registers
separately in light_id_manager.pyp.
"""
import os
import sys

import c4d
from c4d import plugins, gui

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from octanelightdenoiser.c4d_compat.octane_ids import (
    PLUGIN_ID, PLUGIN_NAME, PLUGIN_ID_IDMGR, MENU_TITLE,
)
from octanelightdenoiser.views.main_dialog import OctaneLightDenoiserDialog


def _icon(filename):
    path = os.path.join(_HERE, "res", filename)
    if os.path.exists(path):
        bmp = c4d.bitmaps.BaseBitmap()
        bmp.InitWith(path)
        return bmp
    return None


class DenoiserCommand(plugins.CommandData):
    """Opens the denoiser panel (Build/pass-picker page only)."""

    _dialog = None

    def Execute(self, doc):
        if self._dialog is None:
            self._dialog = OctaneLightDenoiserDialog(mode="build")
        return self._dialog.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID,
                                 defaultw=380, defaulth=720)

    def RestoreLayout(self, sec_ref):
        if self._dialog is None:
            self._dialog = OctaneLightDenoiserDialog(mode="build")
        return self._dialog.Restore(pluginid=PLUGIN_ID, secret=sec_ref)


def _enhance_menu():
    """Add a 'ZHiCK Tool' submenu (with both commands) to the main menu.

    Defensive: if anything fails the commands still appear normally in the
    Extensions menu.
    """
    try:
        main = gui.GetMenuResource("M_EDITOR")
        if main is None:
            return
        sub = c4d.BaseContainer()
        sub.InsData(c4d.MENURESOURCE_SUBTITLE, MENU_TITLE)
        sub.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_%d" % PLUGIN_ID_IDMGR)
        sub.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_%d" % PLUGIN_ID)
        plug = gui.SearchPluginMenuResource()
        if plug is not None:
            main.InsDataAfter(c4d.MENURESOURCE_STRING, sub, plug)
        else:
            main.InsData(c4d.MENURESOURCE_STRING, sub)
    except Exception as exc:  # noqa: BLE001
        print("[ZHiCK Tool] menu build failed: %s" % exc)


def PluginMessage(msg_id, data):
    if msg_id == c4d.C4DPL_BUILDMENU:
        _enhance_menu()
    return True


if __name__ == "__main__":
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=_icon("icon_denoiser.tif"),
        help="Build per-light OIDN denoise Render AOVs (Octane)",
        dat=DenoiserCommand(),
    )
