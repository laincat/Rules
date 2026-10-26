#!/usr/bin/env bash
set -euo pipefail

VERSION="v1.19.33"
SHA256="386508bfb1c72c43b6a0eda73708ecdce82546581b0ebcb16366c53757c622b6"
BASE="https://github.com/MetaCubeX/mihomo/releases/download/${VERSION}"
curl --proto '=https' --tlsv1.2 -fsSL --retry 3 \
  -o mihomo.gz "${BASE}/mihomo-linux-amd64-compatible-${VERSION}.gz"
echo "${SHA256}  mihomo.gz" | sha256sum --check --strict
gzip -dc mihomo.gz > mihomo
chmod +x mihomo
