# Octane Light Denoiser — C4D Plugin

ปลั๊กอิน Cinema 4D ที่ทำให้งาน **"denoise แสงทีละดวง (per-light OIDN)"** ของ Octane
เหลือแค่ **เลือกพาส → ตั้งชื่ออัตโนมัติ → กดปุ่มเดียว** สร้าง Render AOV +
จัดการ Light Pass ID + ตั้งชื่อ EXR layer ให้สื่อความหมาย (เช่น `KeyLight_DN`)

> สถาปัตยกรรมแบบ layered (c4d_compat / models / services / views)

---

## ⚠️ อ่านก่อนใช้ — ยังไม่ผ่านการรันใน C4D จริง

โค้ดนี้เขียนตาม pattern ที่ใช้งานจริง + เขียนแบบ defensive (ไม่ crash)
แต่ **ยังไม่ได้รันทดสอบในเครื่อง C4D** และ Octane ไม่มี Python SDK ทางการ →
**ID บางตัวเป็นค่าตั้งต้นที่ต้องยืนยัน** ทำตามขั้น "Verify" ด้านล่างก่อนใช้งานจริง

---

## ความต้องการ
- Cinema 4D 2024 / 2025 (Python 3.11)
- Octane (c4doctane) — **2024.1 Alpha4+** สำหรับ OIDN compositor (Tier 2);
  Tier 1 (Render AOV + Light ID + naming) ใช้กับเวอร์ชันเก่ากว่าได้

## ติดตั้ง
1. ก๊อปโฟลเดอร์ `OctaneLightDenoiser` ทั้งอันไปไว้ที่ plugins folder:
   - **Windows:** `C:\Users\<you>\AppData\Roaming\Maxon\<version>\plugins\`
   - **macOS:** `~/Library/Preferences/Maxon/<version>/plugins/`
2. รีสตาร์ต Cinema 4D
3. เปิดจากเมนู **Extensions ▸ Octane Light Denoiser** (หรือผ่าน Commander `Shift+C`)

## วิธีใช้ (flow หลัก) — 2 แท็บ: **Manage / Build**
ตั้ง renderer เป็น Octane ใน Render Settings ก่อน แล้วกด **Scan scene**

**แนวคิดสำคัญ:** Light AOV ของ Octane อ้างตาม **Light Pass ID (1–8)** → ไฟที่ **ID เดียวกัน = รวมเป็นพาสเดียว (group)** มีได้ 8 group + Sun + Env

### แท็บ Manage — จัดการไฟ + group
1. เลือกไฟ: ติ๊กในลิสต์ของปลั๊กอิน **หรือ** เปิด "Use scene selection" แล้วเลือกใน Object Manager
2. เลือก ID เป้าหมายจาก dropdown → กด **Assign** (จัดไฟลง group นั้น)
   - **+ New** = ลง ID ว่างถัดไป · **Clear** = เอา ID ออก · **Auto-assign all** = แจก ID unique เร็ว ๆ
3. ตั้งชื่อ group ในช่อง "Groups → passes" → กลายเป็นชื่อพาส

### แท็บ Build — เลือกพาส + สร้าง
4. เห็น **1 แถวต่อ group** + พาสมาตรฐาน จัดกลุ่มตามหมวด (Sun/Env จะเพิ่มภายหลังเมื่อยืนยัน enum)
5. ติ๊กเลือกพาส → แก้ชื่อ output เองได้ หรือปล่อย auto = `<source>_DN`
6. **Build Denoise** = สร้าง Render AOV จริง + ตั้งชื่อ · **Setup EXR** = multipass+EXR · **Inspector** = ดู ID จริง

---

## 🔧 Verify IDs (สำคัญ — ทำครั้งเดียวต่อ build ของ Octane)

กดปุ่ม **Inspector** ในปลั๊กอิน (เลือก object ที่มี Octane Light tag ก่อน) →
มันจะ dump ID จริงลง **Console** (`Script ▸ Console` / `Extensions ▸ Console`)
แล้วแก้ค่าตามจริงในไฟล์เดียว: **`octanelightdenoiser/c4d_compat/octane_ids.py`**

| สิ่งที่ต้องเช็ค | ตัวแปรในไฟล์ | ค่าตั้งต้น (อาจต้องแก้) |
|----------------|-------------|----------------------|
| Plugin ID (ขอจริงจาก PluginCafe) | `PLUGIN_ID` | `1057248` (placeholder) |
| Light Pass ID param บน Light tag | `LIGHTTAG_PASS_ID_CANDIDATES` | เดาไว้หลายตัว |
| Denoise Albedo type | `AOV_DENOISE_ALBEDO` | `191` (DiffF) |
| Denoise Normal type | `AOV_DENOISE_NORMAL` | `236` (Normal shading) |
| Beauty-Surfaces / Render-Layer types | `STANDARD_PASSES` (None) | ยังไม่ใส่ — Build ข้ามให้ |
| Color space "Linear sRGB" | `output_setup._LINEAR_SRGB_GUESS` | `1` |
| Composite/Output-AOV pins (Tier 2) | (ดู `compositor_builder.py`) | ยังไม่ทราบ |

ค่าหลักที่ documented แล้ว (น่าจะถูกเลย): VideoPost `1029525`, AOV shader `1057006`,
Light type `205`, param `3700`/`3740`/`900`/`994`/`995`/`1822`

---

## Tier 2 — OIDN compositor (per-pass denoise node)

ส่วนต่อ node OIDN ในคอมโพสิเตอร์ยังต้องยืนยัน pin IDs ก่อน (ดู `compositor_builder.py`)
วิธีที่แนะนำ = **template-merge**:
1. ต่อกราฟ `Render Output AOV → Open Image Denoiser (+Albedo +Normal) → Output AOV` 1 ครั้งด้วยมือ
2. เซฟซีนเป็น `templates/oidn_group.c4d`
3. ปุ่ม Build จะ merge เทมเพลตนั้นให้ เหลือแค่ repoint source ต่อพาส

ระหว่างนี้ Tier 1 สร้าง Denoise Albedo/Normal + Light AOV ให้ครบแล้ว →
ต่อ OIDN node เองได้ใน 1-2 คลิก

---

## โครงสร้าง
```
OctaneLightDenoiser/
├─ octanelightdenoiser.pyp            entry point (CommandData + dialog)
├─ octanelightdenoiser/
│  ├─ c4d_compat/octane_ids.py        ★ ID ทั้งหมด — แก้ที่นี่ที่เดียว
│  ├─ models/pass_item.py             PassItem / RowState
│  ├─ services/
│  │  ├─ octane_probe.py              detect Octane + Inspector + safe IO
│  │  ├─ light_scanner.py             scan lights + assign Pass IDs + catalog
│  │  ├─ aov_builder.py               สร้าง Render AOV (idempotent, undo)
│  │  ├─ naming.py                    naming engine (manual / {source}_DN)
│  │  ├─ compositor_builder.py        Tier 2 (template-merge)
│  │  ├─ output_setup.py              multipass + EXR
│  │  └─ undo_helper.py               undo grouping
│  └─ views/main_dialog.py            UI (GeDialog)
├─ res/                               c4d_symbols.h + strings
└─ templates/                         วาง oidn_group.c4d ที่นี่ (Tier 2)
```

## หมายเหตุ
- ทุกการเขียน param ผ่าน `safe_set` → ผิด ID ก็ log ไม่ crash
- Build เป็น idempotent (กดซ้ำไม่สร้าง AOV ซ้ำ) + ห่อ undo (1 Ctrl+Z)
- UI เป็น native GeDialog → ได้โครง/พฤติกรรม/state ตาม mockup แต่ chrome (กราดิเอนต์/
  ปุ่มเขียว/มุมโค้ง) เป็นสไตล์ C4D เพราะ native widget ทำ custom styling ไม่ได้
