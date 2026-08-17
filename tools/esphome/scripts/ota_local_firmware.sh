#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESPHOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${ESPHOME_DATA_DIR:-/tmp/aircloud-esphome-data}"
ESPHOME_VERSION="2026.3.3"

usage() {
  echo "Usage: $0 IP_OR_HOSTNAME"
  echo
  echo "Builds hitachi-local.yaml with the saved identity/Wi-Fi credentials and"
  echo "uploads it using ESPHome OTA."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

if ! command -v uvx >/dev/null 2>&1; then
  echo "Error: required command not found: uvx" >&2
  exit 1
fi

CONFIG="hitachi-local.yaml"

if [[ ! -f "${ESPHOME_DIR}/secrets.yaml" ]]; then
  echo "Error: missing ${ESPHOME_DIR}/secrets.yaml" >&2
  exit 1
fi

HOST="$1"
(
  cd "${ESPHOME_DIR}"
  ESPHOME_DATA_DIR="${DATA_DIR}" \
    uvx --from "esphome==${ESPHOME_VERSION}" esphome run \
      "${CONFIG}" \
      --device "${HOST}"
)
