#!/usr/bin/env bash
# Build Jupiter on the host. Everything runs inside a Fedora container so the
# host distro does not matter. livemedia-creator needs root, so podman runs
# with sudo.
#
# Usage: scripts/build-iso.sh [rpms|iso|all]   (default: all)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../distro.conf
source "$ROOT/distro.conf"

STAGE="${1:-all}"
case "$STAGE" in
    rpms|iso|all) ;;
    *) echo "usage: $0 [rpms|iso|all]" >&2; exit 2 ;;
esac

BUILD="$ROOT/build"
mkdir -p "$BUILD/repo" "$BUILD/result"
IMAGE="registry.fedoraproject.org/fedora:${FEDORA_RELEASE}"
PODMAN="${PODMAN:-sudo podman}"

# shellcheck disable=SC2086  # PODMAN may contain several words ("sudo podman")
$PODMAN run --rm --privileged --security-opt label=disable \
    -e FEDORA_RELEASE="$FEDORA_RELEASE" \
    -e DISTRO_VERSION="$DISTRO_VERSION" \
    -e DISTRO_NAME="$DISTRO_NAME" \
    -e ISO_VOLID="$ISO_VOLID" \
    -e STAGE="$STAGE" \
    -v "$ROOT:/src:ro" \
    -v "$BUILD/repo:/jupiter-repo" \
    -v "$BUILD/result:/build/result" \
    "$IMAGE" \
    bash /src/scripts/container-build.sh

if [[ "$STAGE" != "rpms" ]]; then
    iso="$(find "$BUILD/result" -name '*.iso' -print -quit)"
    if [[ -z "$iso" ]]; then
        echo "error: no ISO produced in $BUILD/result" >&2
        exit 1
    fi
    final="$BUILD/result/jupiter-${DISTRO_VERSION}-x86_64.iso"
    [[ "$iso" == "$final" ]] || mv "$iso" "$final"
    echo "ISO: $final"
fi
