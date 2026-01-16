BLENDER_EXE="/c/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"
REPO_DIR="/c/Users/jazza/Documents/Code shit/Cyberpunk-Blender-add-on/release"
ADDON_SRC="../i_scene_cp77_gltf"
ADDON_ZIP="./i_scene_cp77_gltf.zip"
SEVEN_Z="/c/Program Files/7-Zip/7z.exe"

rm -f "$ADDON_ZIP"
"$SEVEN_Z" a -tzip "$ADDON_ZIP" "$ADDON_SRC"

"$BLENDER_EXE" --command extension server-generate --repo-dir="$REPO_DIR"
