#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESPHOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${ESPHOME_DATA_DIR:-/tmp/aircloud-esphome-data}"
DIST_DIR="${ESPHOME_DIST_DIR:-${ESPHOME_DIR}/dist}"
ESPHOME_VERSION="2026.3.3"

usage() {
  echo "Usage: $0"
  echo
  echo "Builds the universal Hitachi production profile configured by secrets.yaml."
  echo "Copies UF2 + SHA-256 to:"
  echo "  ${DIST_DIR}"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command not found: $1" >&2
    exit 1
  fi
}

write_sha256() {
  local file="$1"
  local directory
  local filename
  directory="$(dirname "${file}")"
  filename="$(basename "${file}")"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "${directory}" && sha256sum "${filename}" > "${filename}.sha256")
  else
    (cd "${directory}" && shasum -a 256 "${filename}" > "${filename}.sha256")
  fi
}

build_firmware() {
  local config="hitachi-local.yaml"
  local node
  node="$(
    awk -F':[[:space:]]*' \
      '$1 == "device_name" {gsub(/^[ "'\''"]+|[ "'\''"]+$/, "", $2); print $2; exit}' \
      "${ESPHOME_DIR}/secrets.yaml"
  )"
  if [[ -z "${node}" ]]; then
    echo "Error: unable to read device_name from secrets.yaml" >&2
    exit 1
  fi
  local built="${DATA_DIR}/build/${node}/.pioenvs/${node}/firmware.uf2"
  local output="${DIST_DIR}/${node}-local.uf2"

  echo "Building the universal profile from ${config} for ${node}"
  (
    cd "${ESPHOME_DIR}"
    ESPHOME_DATA_DIR="${DATA_DIR}" \
      uvx --from "esphome==${ESPHOME_VERSION}" esphome compile "${config}"
  )

  if [[ ! -f "${built}" ]]; then
    echo "Error: expected build output not found: ${built}" >&2
    exit 1
  fi

  mkdir -p "${DIST_DIR}"
  cp "${built}" "${output}"
  write_sha256 "${output}"
  echo "Created ${output}"
  echo "Created ${output}.sha256"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 0 ]]; then
  usage >&2
  exit 2
fi

require_command uvx
if [[ ! -f "${ESPHOME_DIR}/secrets.yaml" ]]; then
  echo "Error: missing ${ESPHOME_DIR}/secrets.yaml" >&2
  echo "Run ${SCRIPT_DIR}/configure_local_firmware.sh first." >&2
  exit 1
fi

build_firmware
