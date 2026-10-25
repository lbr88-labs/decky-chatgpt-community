#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(id -u)" -eq 0 ]]; then
    echo "Run this installer as the deck user, not root." >&2
    exit 1
fi
if [[ "${HOME:-}" != "/home/deck" ]]; then
    echo "This local installer only writes below /home/deck/homebrew/plugins." >&2
    exit 1
fi
if [[ ! -f "${repo_root}/dist/index.js" ]]; then
    echo "Missing dist/index.js; run pnpm run build first." >&2
    exit 1
fi

target="/home/deck/homebrew/plugins/decky-chatgpt-community"
if [[ "${target}" != "/home/deck/homebrew/plugins/decky-chatgpt-community" ]]; then
    echo "Refusing unexpected plugin target: ${target}" >&2
    exit 1
fi

mkdir -p "${target}/backend" "${target}/dist" "${target}/assets"
install -m 0644 "${repo_root}/dist/index.js" "${target}/dist/index.js"
install -m 0644 "${repo_root}/main.py" "${target}/main.py"
install -m 0644 "${repo_root}/plugin.json" "${target}/plugin.json"
install -m 0644 "${repo_root}/package.json" "${target}/package.json"
install -m 0644 "${repo_root}/README.md" "${target}/README.md"
install -m 0644 "${repo_root}/LICENSE" "${target}/LICENSE"
install -m 0644 "${repo_root}/assets/logo.svg" "${target}/assets/logo.svg"

for module in __init__ compatibility controller desktop installations models processes status; do
    install -m 0644 "${repo_root}/backend/${module}.py" "${target}/backend/${module}.py"
done
install -m 0644 "${repo_root}/backend/sessions.py" "${target}/backend/sessions.py"
install -m 0644 "${repo_root}/backend/voice_controls.mjs" "${target}/backend/voice_controls.mjs"

echo "Installed ChatGPT Community for Decky at ${target}"
echo "Restart Decky Loader or reboot the Steam Deck to load it."
