"""Central registry of every numeric ID + the pass catalog.

Octane has **no official Python SDK**; these IDs are community-verified and
stable in practice, but NOT contractual. Anything marked ``# VERIFY`` should be
confirmed on *your* Octane build with the built-in Inspector (Build tab ▸
"Inspector", or ``services.octane_probe.OctaneProbe.inspect``).
Keeping every ID here means a fix is a one-line edit.
"""
from __future__ import annotations

# ===================================================================== plugin
PLUGIN_ID: int = 1057248      # PLACEHOLDER — request a real ID from
                              # https://plugincafe.maxon.net before release.
PLUGIN_NAME: str = "Octane Light Denoiser"

# ============================================================ Octane handles
OCTANE_VIDEO_POST: int     = 1029525   # renderer VideoPost (host of all AOVs)
OCTANE_RENDERPASS_AOV: int = 1057006   # BaseShader type for a Render AOV node
OCTANE_LIGHT_TAG: int      = 1029526   # Octane Light tag (holds Light Pass ID)

SYMBOL_VIDEO_POST = ("ID_OCTANE_VIDEO_POST", "VPocta")
SYMBOL_RENDERPASS = ("ID_OCTANE_RENDERPASS_AOV", "RENDERAOV")
SYMBOL_LIGHT_TAG  = ("ID_OCTANE_LIGHT_TAG", "Octane_LightTag", "OctaneLightTag")

# ---- VideoPost parameters (Render AOV system) ----
SET_RENDERAOV_IN_CNT: int  = 3700
SET_RENDERAOV_INPUT_0: int = 3740
VP_BUFFER_TYPE: int        = 1010
VP_COLOR_SPACE: int        = 1028

# ---- per-AOV shader parameters ----
RNDAOV_NAME: int      = 900            # str -> EXR layer name
RNDAOV_ENABLED: int   = 994
RNDAOV_TYPE: int      = 995
RNDAOV_TYPE_NAME: int = 1101
RNDAOV_LIGHT_ID: int  = 1822           # Light Pass ID (1..8) on a Light AOV

# ---- Light-tag "Light Pass ID" parameter ----
# Octane injects its symbols into the `c4d` namespace (confirmed: e.g.
# c4d.OBJECTTAG_LIGHTID_1), so we resolve this param by NAME first (correct on
# any build), then fall back to numeric guesses, then the Inspector.
# Research-confirmed: lights sharing this ID render as ONE combined Light pass.
LIGHTTAG_PASS_ID_SYMBOLS: tuple = (
    "LIGHTTAG_LIGHT_PASS_ID", "LIGHTTAG_LIGHTID", "LIGHTTAG_LIGHT_ID",
    "LIGHTTAG_PASS_ID", "LIGHTTAG_LIGHTPASSID",
    "OCT_LIGHTTAG_LIGHTID", "OCT_LIGHTTAG_LIGHT_PASS_ID",
)
LIGHTTAG_PASS_ID_CANDIDATES: tuple = (1424, 1425, 1426, 705, 706, 1000)  # numeric fallback # VERIFY

# ===================================================== AOV type values (RNDAOV_TYPE)
AOV_LIGHT           = 205
AOV_LIGHT_DIRECT    = 206
AOV_LIGHT_INDIRECT  = 208
AOV_LIGHT_PASS_ID   = 209
AOV_BEAUTY_DENOISER = 3380
AOV_DENOISE_ALBEDO  = 191   # "Diffuse filter (info)" / DiffF   # VERIFY
AOV_DENOISE_NORMAL  = 236   # "Normal (shading)"                # VERIFY
AOV_NORMAL_GEO      = 198
AOV_DIFFUSE    = 188
AOV_REFLECTION = 222
AOV_REFRACTION = 229
AOV_SSS        = 238
AOV_SHADOW     = 237
AOV_EMISSION   = 196
AOV_POSITION    = 220
AOV_ZDEPTH      = 255
AOV_MOTION      = 211
AOV_OBJECT_ID   = 217
AOV_MATERIAL_ID = 210

LIGHT_SUN = "Sun"
LIGHT_ENV = "Env"
MAX_LIGHT_IDS = 8

# ===================================================== pass catalog (mirrors data.js)
GROUPS = [
    ("LIGHT",           "Light"),
    ("AUXILIARY",       "Auxiliary"),
    ("BEAUTY",          "Beauty"),
    ("BEAUTY-SURFACES", "Beauty · Surfaces"),
    ("INFO",            "Info"),
    ("RENDER-LAYER",    "Render Layer"),
]
DEFAULT_OPEN = ("LIGHT", "AUXILIARY", "BEAUTY")

# (cat, source, aov_type, required). aov_type=None => shown but Build skips it.
STANDARD_PASSES = [
    ("AUXILIARY", "Denoise Albedo", AOV_DENOISE_ALBEDO, True),
    ("AUXILIARY", "Denoise Normal", AOV_DENOISE_NORMAL, True),

    ("BEAUTY", "Diffuse",    AOV_DIFFUSE,    False),
    ("BEAUTY", "Reflection", AOV_REFLECTION, False),
    ("BEAUTY", "Refraction", AOV_REFRACTION, False),
    ("BEAUTY", "Emission",   AOV_EMISSION,   False),
    ("BEAUTY", "SSS",        AOV_SSS,        False),
    ("BEAUTY", "Shadow",     AOV_SHADOW,     False),

    ("BEAUTY-SURFACES", "Reflection Direct",   None, False),  # VERIFY type
    ("BEAUTY-SURFACES", "Reflection Indirect", None, False),  # VERIFY type
    ("BEAUTY-SURFACES", "Diffuse Direct",      None, False),  # VERIFY type
    ("BEAUTY-SURFACES", "Diffuse Indirect",    None, False),  # VERIFY type

    ("INFO", "Z-Depth",       AOV_ZDEPTH,         False),
    ("INFO", "Normal",        AOV_DENOISE_NORMAL, False),
    ("INFO", "Position",      AOV_POSITION,       False),
    ("INFO", "Motion Vector", AOV_MOTION,         False),
    ("INFO", "Object ID",     AOV_OBJECT_ID,      False),
    ("INFO", "Material ID",   AOV_MATERIAL_ID,    False),

    ("RENDER-LAYER", "Foreground", None, False),  # VERIFY type
    ("RENDER-LAYER", "Background", None, False),  # VERIFY type
]

# =============================================================== dialog widget IDs
# -- Header (Zone 1) --
ID_HEADER_GROUP = 1000
ID_APPTITLE     = 1001
ID_APPSUB       = 1002
ID_STATUS_PILL  = 1003
ID_SCAN_BTN     = 1004

# -- Build-tab toolbar (Zone 2) --
ID_TOOLBAR_GROUP = 1010
ID_SEL_ALL       = 1011
ID_SEL_NONE      = 1012
ID_AUTONAME_ALL  = 1013
ID_SEARCH        = 1014

# -- Build-tab list (Zone 3) --
ID_LIST_SCROLL = 1020
ID_LIST_GROUP  = 1021
ID_BANNER      = 1022
ID_EMPTY_TEXT  = 1025

# -- Build-tab footer (Zone 4) --
ID_SETUP_EXR   = 1032
ID_BUILD       = 1033
ID_FOOT_STATUS = 1034
ID_INSPECTOR   = 1036

# -- Tabs --
ID_TABBAR_GROUP = 1040
ID_TAB_MANAGE   = 1041
ID_TAB_BUILD    = 1042
ID_BODY         = 1043     # flushable body; content depends on the active tab

# -- Manage-tab controls --
ID_MGR_USESCENE = 1050
ID_MGR_IDCOMBO  = 1051
ID_MGR_ASSIGN   = 1052
ID_MGR_NEW      = 1053
ID_MGR_CLEAR    = 1054
ID_MGR_AUTO     = 1055
ID_MGR_SELALL   = 1056
ID_MGR_SELNONE  = 1057
ID_MGR_SCROLL   = 1058
ID_MGR_LIST     = 1059
ID_MGR_STATUS   = 1060

# -- Dynamic ranges (each base owns a 10000-id window; no overlap) --
ID_GROUP_HEAD_BASE = 3000          # build-tab category header = base + group_index

ID_ROW_BASE   = 10000              # build-tab pass rows (10000..19999)
ID_ROW_STRIDE = 8
ROW_OFF_CHK    = 0
ROW_OFF_NAME   = 1
ROW_OFF_ACTION = 2
ROW_OFF_INFO   = 3
ROW_OFF_ERR    = 4

ID_MLIGHT_BASE   = 20000           # manage-tab light rows (20000..29999)
ID_MLIGHT_STRIDE = 4
MROW_OFF_CHK  = 0                  # light select checkbox (label = light name)
MROW_OFF_INFO = 1                  # current-ID tag

ID_GROUP_ROW_BASE   = 30000        # manage-tab group rows (30000..39999)
ID_GROUP_ROW_STRIDE = 4
GROW_OFF_NAME = 0                  # editable group name (-> pass name)
GROW_OFF_INFO = 1

_WINDOW = 10000


def group_head_id(group_index: int) -> int:
    return ID_GROUP_HEAD_BASE + group_index


def row_widget_id(row_index: int, offset: int) -> int:
    return ID_ROW_BASE + row_index * ID_ROW_STRIDE + offset


def is_row_widget(widget_id: int) -> bool:
    return ID_ROW_BASE <= widget_id < ID_ROW_BASE + _WINDOW


def decode_row_widget(widget_id: int):
    rel = widget_id - ID_ROW_BASE
    return rel // ID_ROW_STRIDE, rel % ID_ROW_STRIDE


def mlight_id(row_index: int, offset: int) -> int:
    return ID_MLIGHT_BASE + row_index * ID_MLIGHT_STRIDE + offset


def is_mlight(widget_id: int) -> bool:
    return ID_MLIGHT_BASE <= widget_id < ID_MLIGHT_BASE + _WINDOW


def decode_mlight(widget_id: int):
    rel = widget_id - ID_MLIGHT_BASE
    return rel // ID_MLIGHT_STRIDE, rel % ID_MLIGHT_STRIDE


def group_row_id(row_index: int, offset: int) -> int:
    return ID_GROUP_ROW_BASE + row_index * ID_GROUP_ROW_STRIDE + offset


def is_group_row(widget_id: int) -> bool:
    return ID_GROUP_ROW_BASE <= widget_id < ID_GROUP_ROW_BASE + _WINDOW


def decode_group_row(widget_id: int):
    rel = widget_id - ID_GROUP_ROW_BASE
    return rel // ID_GROUP_ROW_STRIDE, rel % ID_GROUP_ROW_STRIDE
