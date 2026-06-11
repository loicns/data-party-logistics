#!/usr/bin/env bash
# Pre-deploy guard: every compiled extension in the SAM build output must be
# Linux aarch64 ELF. A host-arch wheel (macOS or x86_64) sneaking in is exactly
# what caused the 2-day AIS ingestion outage (pydantic_core ImportModuleError).
#
# Usage: scripts/check_wheel_arch.sh [build_dir]   (default .aws-sam/build)
set -euo pipefail

BUILD_DIR="${1:-.aws-sam/build}"
[ -d "$BUILD_DIR" ] || { echo "ERROR: $BUILD_DIR not found — run 'sam build' first"; exit 1; }

bad=0
checked=0
while IFS= read -r -d '' so; do
  checked=$((checked + 1))
  info="$(file -b "$so")"
  case "$info" in
    *"ELF 64-bit"*"aarch64"*) ;;  # correct target
    *)
      echo "WRONG ARCH: $so"
      echo "    -> $info"
      bad=$((bad + 1))
      ;;
  esac
done < <(find "$BUILD_DIR" -name "*.so" -print0)

echo "checked $checked native libraries in $BUILD_DIR"
if [ "$bad" -gt 0 ]; then
  echo "FAIL: $bad native librar(y/ies) are not Linux aarch64 — Lambda (arm64) will crash at import."
  echo "Fix: the Makefile must install with --platform manylinux2014_aarch64 --only-binary=:all:"
  exit 1
fi
echo "OK: all native libraries are Linux aarch64."
