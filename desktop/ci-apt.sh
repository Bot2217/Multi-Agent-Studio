#!/usr/bin/env bash
# Install the Linux libraries Tauri needs. GitHub-hosted Ubuntu images sometimes
# point apt at http://azure.archive.ubuntu.com, which drops connections. Retry
# against HTTPS mirrors instead of waiting on that one host.
set -euo pipefail

sudo systemctl stop apt-daily.timer apt-daily-upgrade.timer \
  apt-daily.service apt-daily-upgrade.service || true

if [[ -f /etc/apt/apt-mirrors.txt ]]; then
  printf '%s\n' \
    'https://archive.ubuntu.com/ubuntu' \
    'https://mirror.ubuntu.com/ubuntu' \
    'https://mirrors.kernel.org/ubuntu' \
    | sudo tee /etc/apt/apt-mirrors.txt >/dev/null
fi

while IFS= read -r -d '' sources; do
  sudo sed -i \
    -e 's|http://azure.archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
    -e 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
    -e 's|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' \
    "$sources"
done < <(sudo find /etc/apt -type f \( -name 'sources.list' -o -name '*.list' -o -name '*.sources' \) -print0)

APT_OPTS=(
  -o Acquire::Retries=5
  -o Acquire::http::Timeout=20
  -o Acquire::https::Timeout=20
  -o Acquire::ForceIPv4=true
)

update_ok=0
for attempt in 1 2 3 4 5; do
  if sudo DEBIAN_FRONTEND=noninteractive apt-get update "${APT_OPTS[@]}"; then
    update_ok=1
    break
  fi
  echo "apt-get update failed, attempt ${attempt}; retrying"
  sleep $((attempt * 10))
done
if [[ "$update_ok" != 1 ]]; then
  echo "apt-get update failed after retries" >&2
  exit 1
fi

install_ok=0
for attempt in 1 2 3 4 5; do
  if sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    -o Dpkg::Options::=--force-confdef \
    -o Dpkg::Options::=--force-confold \
    "${APT_OPTS[@]}" \
    libwebkit2gtk-4.1-dev \
    libgtk-3-dev \
    librsvg2-dev \
    patchelf \
    build-essential; then
    install_ok=1
    break
  fi
  echo "apt-get install failed, attempt ${attempt}; retrying"
  sleep $((attempt * 15))
done
if [[ "$install_ok" != 1 ]]; then
  echo "apt-get install failed after retries" >&2
  exit 1
fi
