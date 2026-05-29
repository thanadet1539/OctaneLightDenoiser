"""Octane Light Denoiser — Cinema 4D plugin entry point.

Registers the CommandData that opens the panel (Extensions menu / Commander).

PLUGIN ID is a development PLACEHOLDER (see c4d_compat/octane_ids.py) —
request a real one from https://plugincafe.maxon.net before sharing.
"""
import os
import sys

import c4d
from c4d import plugins, gui  # noqa: F401  (gui kept for parity / future use)

# Make the package importable from this .pyp file's folder.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from octanelightdenoiser.c4d_compat.octane_ids import PLUGIN_ID, PLUGIN_NAME
from octanelightdenoiser.views.main_dialog import OctaneLightDenoiserDialog


class OctaneLightDenoiserCommand(plugins.CommandData):
    """Opens the panel. The async dialog is reused across invocations."""

    _dialog = None

    def Execute(self, doc):
        if self._dialog is None:
            self._dialog = OctaneLightDenoiserDialog()
        return self._dialog.Open(
            dlgtype=c4d.DLG_TYPE_ASYNC,
            pluginid=PLUGIN_ID,
            defaultw=360,
            defaulth=680,
        )

    def RestoreLayout(self, sec_ref):
        if self._dialog is None:
            self._dialog = OctaneLightDenoiserDialog()
        return self._dialog.Restore(pluginid=PLUGIN_ID, secret=sec_ref)


if __name__ == "__main__":
    icon_path = os.path.join(_HERE, "res", "icon.tif")
    icon = c4d.bitmaps.BaseBitmap()
    if os.path.exists(icon_path):
        icon.InitWith(icon_path)
    else:
        icon = None

    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=icon,
        help="Automate per-light OIDN denoise AOVs (Octane)",
        dat=OctaneLightDenoiserCommand(),
    )
