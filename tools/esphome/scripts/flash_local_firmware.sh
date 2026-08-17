#!/usr/bin/env bash
set -euo pipefail

FLASH_SIZE=2097152
BAUD_RATE=115200

usage() {
  echo "Usage: $0 SERIAL_PORT FIRMWARE_UF2 BACKUP_PASS1 BACKUP_PASS2"
  echo
  echo "Validates two matching full backups and then writes a local ESPHome UF2."
  echo "The board must already be in ROM download mode."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 4 ]]; then
  usage >&2
  exit 2
fi

if ! command -v uvx >/dev/null 2>&1; then
  echo "Error: required command not found: uvx" >&2
  exit 1
fi

PORT="$1"
FIRMWARE="$2"
BACKUP1="$3"
BACKUP2="$4"
LTC=(uvx --from ltchiptool ltchiptool)

for file in "${FIRMWARE}" "${BACKUP1}" "${BACKUP2}"; do
  if [[ ! -f "${file}" ]]; then
    echo "Error: file not found: ${file}" >&2
    exit 1
  fi
done

SIZE1="$(wc -c < "${BACKUP1}" | tr -d '[:space:]')"
SIZE2="$(wc -c < "${BACKUP2}" | tr -d '[:space:]')"
if [[ "${SIZE1}" -ne "${FLASH_SIZE}" || "${SIZE2}" -ne "${FLASH_SIZE}" ]]; then
  echo "Error: backups must both be complete ${FLASH_SIZE}-byte flash images." >&2
  exit 1
fi

if ! cmp -s "${BACKUP1}" "${BACKUP2}"; then
  echo "Error: backup files are not byte-identical. Refusing to flash." >&2
  exit 1
fi

echo "Validating UF2 metadata"
"${LTC[@]}" uf2 info "${FIRMWARE}"

echo
echo "WARNING: this replaces the application firmware on ${PORT}."
echo "The module must be disconnected from the air conditioner and powered at 3.3 V only."
read -r -p "Type FLASH to continue: " CONFIRMATION
if [[ "${CONFIRMATION}" != "FLASH" ]]; then
  echo "Cancelled."
  exit 1
fi

"${LTC[@]}" flash write \
  -d "${PORT}" \
  -b "${BAUD_RATE}" \
  "${FIRMWARE}"

echo "Write completed and verified."
echo "Remove bench power and all programming wires before reinstalling the module."
