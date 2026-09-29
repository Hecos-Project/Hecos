import os

base_dir = r"C:\Hecos\hecos\modules\web_ui\static\js"
gp_file = os.path.join(base_dir, "global_presets.js")

with open(gp_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

blocks = {}
current_block = []
current_func = "head"

for line in lines:
    if line.startswith("window.") and "=" in line and "function" in line:
        if current_block:
            blocks[current_func] = "".join(current_block)
        current_block = [line]
        current_func = line.split("=")[0].replace("window.", "").strip()
    else:
        current_block.append(line)

if current_block:
    blocks[current_func] = "".join(current_block)

files = {
    "gp_state.js": ["head", "sfLoadData", "sfLoadActiveSessionState", "sfActivateSoul"],
    "gp_ui.js": ["sfTogglePanel", "sfDirty", "sfUpdateSliderVal", "sfPopulateDropdowns", "sfUpdateModelsDropdown", "sfUpdateVoicesDropdown", "sfApplySoulToUI", "sfCollectUIState", "sfApplyInferencePreset", "sfApplyXttsPreset", "sfApplyXttsInferencePreset"],
    "gp_actions.js": ["sfSaveAsNewSoul", "sfSaveInlineToActive", "sfOverwriteSoul", "sfDeleteSoul"],
    "gp_xtts.js": ["sfSaveNewXttsInferencePreset", "sfOverwriteXttsInferencePreset", "sfDeleteXttsInferencePreset"]
}

out_dir = os.path.join(base_dir, "global_presets")
os.makedirs(out_dir, exist_ok=True)

for fname, func_names in files.items():
    with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
        f.write(f"/* ⚡ SOUL FORGE: {fname} */\n\n")
        for func in func_names:
            if func in blocks:
                f.write(blocks[func])
                f.write("\n")
            else:
                print(f"Function {func} not found!")

print("Split completed successfully!")
