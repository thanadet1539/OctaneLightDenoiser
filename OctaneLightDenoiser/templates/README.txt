Tier 2 — OIDN compositor template
==================================

Drop a file named  oidn_group.c4d  in this folder to enable auto-merge of a
hand-built denoise group when you press "Build Denoise".

How to make it (once):
  1. In Render Settings ▸ Octane ▸ Output AOV Compositor, build ONE group:
       Render Output AOV  ->  Open Image Denoiser (connect Albedo + Normal)
                          ->  Output AOV
  2. Connect the Albedo / Normal pins to the Denoise Albedo / Denoise Normal
     Render AOVs (the plugin creates those for you in Tier 1).
  3. Save the scene as:  oidn_group.c4d  in this folder.

On Build, the plugin merges that group into the current scene; you then repoint
each Render-Output-AOV's source to the matching Light AOV (1-2 clicks each).

This sidesteps the unverified composite-pin IDs entirely.
