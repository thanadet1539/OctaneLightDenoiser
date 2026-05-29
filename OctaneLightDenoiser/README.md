# ZHiCK Tool — Octane Light Denoiser + Light ID Manager

ปลั๊กอิน Cinema 4D **2 ตัว** สำหรับ workflow "denoise แสงทีละดวง" ของ Octane
หลังติดตั้งจะอยู่ใต้เมนู **Extensions ▸ ZHiCK Tool**:

1. **Octane Light ID Manager** — จัดกลุ่มไฟตาม Light Pass ID (ไฟ ID เดียวกัน = พาสเดียว)
2. **Octane Light Denoiser** — เลือกพาส + ตั้งชื่ออัตโนมัติ + สร้าง Render AOV (`_DN`) + ตั้งค่า EXR

> สถาปัตยกรรมแบบ layered (c4d_compat / models / services / views) — 2 ปลั๊กอินใช้แพ็กเกจร่วมกัน

---

## ⚠️ อ่านก่อน — Octane ไม่มี Python API ทางการ
ID หลักยืนยันแล้ว (กับ DunHou octane_id.py) แต่บางตัวยัง resolve-by-name/เดา
(โดยเฉพาะ Light-tag "Light Pass ID" param) → กด **Inspector** (ในตัว Denoiser) เพื่อดู ID จริง

## ความต้องการ
- Cinema 4D 2024+ (Python 3.11) · Octane (c4doctane) 2024.x / 24.x (24.12 R+)

## ติดตั้ง
ก๊อปโฟลเดอร์นี้ทั้งอันไป `…\Maxon\<version>\plugins\` → รีสตาร์ต C4D
(หรือใช้ install.bat / web_install.ps1 จาก repo)

## วิธีใช้ (2 ปลั๊กอิน ทำตามลำดับ)
**1) Extensions ▸ ZHiCK Tool ▸ Octane Light ID Manager**
- Scan → ติ๊กไฟ (หรือเปิด "Use scene selection" เลือกใน Object Manager) → เลือก ID → **Assign**
- หรือ **Auto-assign all** แจก ID อัตโนมัติ · ตั้งชื่อ group ได้ (กลายเป็นชื่อพาส)
- ถ้าไฟยังไม่มี Octane Light tag จะถูกสร้างให้ตอน Assign

**2) Extensions ▸ ZHiCK Tool ▸ Octane Light Denoiser**
- Scan → เห็นพาส: กลุ่มไฟ (จากขั้น 1) + Denoise Albedo/Normal + พาสมาตรฐาน
- ติ๊กพาส → แก้ชื่อหรือปล่อย auto (`<source>_DN`) → **Build Denoise** (สร้าง Render AOV จริง)
- **Setup EXR** = multipass + EXR · **Inspector** = ดู/debug ID จริง

## โครงสร้าง
```
OctaneLightDenoiser/
├─ light_denoiser.pyp        ปลั๊กอิน Denoiser + เมนู "ZHiCK Tool"
├─ light_id_manager.pyp      ปลั๊กอิน Light ID Manager
├─ octanelightdenoiser/      แพ็กเกจร่วม (c4d_compat / models / services / views)
├─ res/                      icon_denoiser.tif · icon_idmgr.tif · c4d_symbols.h
└─ templates/                วาง oidn_group.c4d สำหรับ Tier 2 (template-merge)
```

## หมายเหตุ
- ทุกการเขียน param ผ่าน `safe_set` (ผิด ID ก็ log ไม่ crash) · Build idempotent + undo
- UI เป็น native GeDialog (โครง/พฤติกรรมตาม mockup; chrome เป็นสไตล์ C4D)
- **Tier 2** (ต่อ node OIDN ในคอมโพสิเตอร์อัตโนมัติ) อยู่ระหว่างทำ — รอยืนยัน composite pins
  ผ่าน Inspector; ตอนนี้สร้าง Light AOV + Denoise Albedo/Normal (ของที่ OIDN ต้องใช้) ให้ครบแล้ว
