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

# Check if we're running as root (podman needs root or rootless with specific setup)
if [ "$(id -u)" -ne 0 ]; then
    if ! command -v podman &>/dev/null && ! command -v docker &>/dev/null; then
        echo "error: podman or docker not found" >&2
        exit 1
    fi
fi

IMAGE="registry.fedoraproject.org/fedora:${FEDORA_RELEASE}"
PODMAN="${PODMAN:-sudo podman}"

# Check if the Fedora image exists locally (saves time if it does)
echo "==> Checking for Fedora image: $IMAGE"
if ! $PODMAN image inspect "$IMAGE" &>/dev/null; then
    echo "error: Fedora image not found locally. Pulling..." >&2
    $PODMAN pull "$IMAGE" || {
        echo "error: failed to pull Fedora image" >&2
        exit 1
    }
fi

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
    bash /src/scripts/container-build.sh || {
    echo "error: container build failed" >&2
    exit 1
}

if [[ "$STAGE" != "rpms" ]]; then
    iso="$(find "$BUILD/result" -name '*.iso' -print -quit)"
    if [[ -z "$iso" ]]; then
        echo "error: no ISO produced in $BUILD/result" >&2
        exit 1
    fi
    final="$BUILD/result/jupiter-${DISTRO_VERSION}-x86_64.iso"
    [[ "$iso" == "$final" ]] || mv "$iso" "$final"
    echo "ISO: $final"
    
    # Verify the ISO is a valid ISO image
    if ! file "$final" | grep -q "ISO 9660"; then
        echo "error: $final does not appear to be a valid ISO image" >&2
        exit 1
    fi
fi
