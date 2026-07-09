#!/usr/bin/env bash
set -euo pipefail

mkdir -p modules

clone_or_pull() {
  local repo_url="$1"
  local folder="$2"

  if [ -d "modules/$folder/.git" ]; then
    echo "Updating modules/$folder"
    git -C "modules/$folder" pull --ff-only || true
  else
    echo "Cloning $repo_url -> modules/$folder"
    git clone "$repo_url" "modules/$folder"
  fi
}

clone_or_pull "https://github.com/amanbhardwaj-coder/Smiling_Rocks.git" "Smiling_Rocks"
clone_or_pull "https://github.com/amanbhardwaj-coder/inventory-toolAI.git" "inventory-toolAI"
clone_or_pull "https://github.com/amanbhardwaj-coder/inventory-tool2.0.git" "inventory-tool2.0"
clone_or_pull "https://github.com/amanbhardwaj-coder/inventory-tool.git" "inventory-tool"
clone_or_pull "https://github.com/amanbhardwaj-coder/file_merge.git" "file_merge"
clone_or_pull "https://github.com/amanbhardwaj-coder/Excelsplitter.git" "Excelsplitter"
clone_or_pull "https://github.com/amanbhardwaj-coder/URL_Checker.git" "URL_Checker"
clone_or_pull "https://github.com/amanbhardwaj-coder/Jsontocsv.git" "Jsontocsv"
clone_or_pull "https://github.com/amanbhardwaj-coder/Jewelry_filter_creation.git" "Jewelry_filter_creation"
clone_or_pull "https://github.com/amanbhardwaj-coder/JL.git" "JL"

echo "Done. Run: streamlit run Dashboard.py"
