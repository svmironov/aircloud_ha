#!/usr/bin/env bash
set -euo pipefail

FLASH_SIZE=2097152
BAUD_RATE=115200

usage() {
  echo "Usage: $0 SERIAL_PORT OUTPUT_DIRECTORY"
  echo
  echo "Reads the complete 2 MiB AmebaZ flash twice and requires byte-identical dumps."
  echo "The board must already be in ROM download mode."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 2 ]]; then
  usage >&2
  exit 2
fi

if ! command -v uvx >/dev/null 2>&1; then
  echo "Error: required command not found: uvx" >&2
  exit 1
fi

PORT="$1"
OUTPUT_DIR="$2"
PASS1="${OUTPUT_DIR}/stock-pass1.bin"
PASS2="${OUTPUT_DIR}/stock-pass2.bin"
LTC=(uvx --from ltchiptool ltchiptool)

if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Error: output directory already exists; refusing to overwrite: ${OUTPUT_DIR}" >&2
  exit 1
fi

echo "Reading chip information from ${PORT}"
"${LTC[@]}" flash info -d "${PORT}" -b "${BAUD_RATE}" ambz

mkdir -p "${OUTPUT_DIR}"

echo "Reading full flash: pass 1"
"${LTC[@]}" flash read \
  -d "${PORT}" \
  -b "${BAUD_RATE}" \
  -l 0x200000 \
  ambz \
  "${PASS1}"

echo "Reading full flash: pass 2"
"${LTC[@]}" flash read \
  -d "${PORT}" \
  -b "${BAUD_RATE}" \
  -l 0x200000 \
  ambz \
  "${PASS2}"

SIZE1="$(wc -c < "${PASS1}" | tr -d '[:space:]')"
SIZE2="$(wc -c < "${PASS2}" | tr -d '[:space:]')"
if [[ "${SIZE1}" -ne "${FLASH_SIZE}" || "${SIZE2}" -ne "${FLASH_SIZE}" ]]; then
  echo "Error: expected two ${FLASH_SIZE}-byte dumps, got ${SIZE1} and ${SIZE2}." >&2
  exit 1
fi

if ! cmp -s "${PASS1}" "${PASS2}"; then
  echo "Error: the two flash reads differ. Keep both files and repeat the backup." >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  (cd "${OUTPUT_DIR}" && sha256sum stock-pass1.bin stock-pass2.bin > SHA256SUMS)
else
  (cd "${OUTPUT_DIR}" && shasum -a 256 stock-pass1.bin stock-pass2.bin > SHA256SUMS)
fi

echo "Backup verified: both complete flash reads are byte-identical."
echo "Files: ${PASS1}, ${PASS2}, ${OUTPUT_DIR}/SHA256SUMS"
echo "Store another copy outside this repository and never publish these dumps."
