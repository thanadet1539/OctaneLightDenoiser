"""Octane Light ID Manager — group lights by Light Pass ID  (ZHiCK Tool).

Sibling of light_denoiser.pyp; shares the same package. The "ZHiCK Tool"
submenu is built in light_denoiser.pyp (single owner, avoids duplicates).
"""
import os
import sys

import c4d
from c4d import plugins

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from octanelightdenoiser.c4d_compat.octane_ids import PLUGIN_ID_IDMGR, PLUGIN_NAME_IDMGR
from octanelightdenoiser.views.main_dialog import OctaneLightDenoiserDialog


def _icon(filename):
    path = os.path.join(_HERE, "res", filename)
    if os.path.exists(path):
        bmp = c4d.bitmaps.BaseBitmap()
        bmp.InitWith(path)
        return bmp
    return None


class LightIDManagerCommand(plugins.CommandData):
    """Opens the Light ID Manager panel (Manage page only)."""

    _dialog = None

    def Execute(self, doc):
        if self._dialog is None:
            self._dialog = OctaneLightDenoiserDialog(mode="manage")
        return self._dialog.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID_IDMGR,
                                 defaultw=380, defaulth=620)

    def RestoreLayout(self, sec_ref):
        if self._dialog is None:
            self._dialog = OctaneLightDenoiserDialog(mode="manage")
        return self._dialog.Restore(pluginid=PLUGIN_ID_IDMGR, secret=sec_ref)


if __name__ == "__main__":
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID_IDMGR,
        str=PLUGIN_NAME_IDMGR,
        info=0,
        icon=_icon("icon_idmgr.tif"),
        help="Assign & group Octane lights by Light Pass ID",
        dat=LightIDManagerCommand(),
    )
