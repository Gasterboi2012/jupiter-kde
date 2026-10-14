#!/usr/bin/env bash
# Runs inside the Fedora builder container (see scripts/build-iso.sh).
# Inputs: /src (read-only repo), /jupiter-repo (local RPM repo), /build/result.
set -euo pipefail

: "${FEDORA_RELEASE:?}" "${DISTRO_VERSION:?}" "${ISO_VOLID:?}" "${STAGE:?}"

echo "==> installing build tools"
dnf -y install rpm-build rpmdevtools createrepo_c pykickstart lorax-lmc-novirt tar gzip

TOP=/tmp/rpmbuild
trap "rm -rf \"$TOP\"" EXIT
mkdir -p "$TOP"/{SOURCES,SPECS,BUILD,RPMS,SRPMS}

# Check disk space before RPM build (need ~5GB free for rpmbuild)
available_space=$(df -BG "$TOP" | awk 'NR==2 {print $2}' | tr -d 'G')
if [ "$available_space" -lt 5 ]; then
    echo "error: insufficient disk space (need ~5GB, have ${available_space}GB)" >&2
    exit 1
fi

# make_tarball <name-version> <source-dir>: archive the dir under <name-version>/
make_tarball() {
    local name="$1" dir="$2"
    tar -C "$dir" --transform "s,^\.\/,$name/, " --exclude=__pycache__ --exclude='*.pyc' \
        -czf "$TOP/SOURCES/$name.tar.gz" .
}

build_rpm() {
    local spec="$1"
    dnf -y builddep "$spec" || {
        echo "error: failed to build dependencies for $spec" >&2
        return 1
    }
    rpmbuild -bb --define "_topdir $TOP" "$spec" || {
        echo "error: failed to build RPM from $spec" >&2
        return 1
    }
}

build_rpms() {
    echo "==> building RPMs"
    make_tarball "jupiter-branding-0.1" "/src/packaging/jupiter-branding/files"
    cp /src/packaging/jupiter-branding/jupiter-branding.spec "$TOP/SPECS/"
    build_rpm "$TOP/SPECS/jupiter-branding.spec" || {
        echo "error: failed to build jupiter-branding RPM" >&2
        exit 1
    }

    make_tarball "jupiter-installer-0.1.0" "/src/installer"
    cp /src/packaging/jupiter-installer/jupiter-installer.spec "$TOP/SPECS/"
    build_rpm "$TOP/SPECS/jupiter-installer.spec" || {
        echo "error: failed to build jupiter-installer RPM" >&2
        exit 1
    }

    cp "$TOP/RPMS"/*.rpm /jupiter-repo/
    createrepo_c --update /jupiter-repo
}

validate_kickstart() {
    echo "==> validating kickstart"
    if ! ksvalidator --version "F${FEDORA_RELEASE}" /src/kickstart/jupiter-live.ks; then
        echo "error: kickstart validation failed" >&2
        exit 1
    fi
}

build_iso() {
    echo "==> building live ISO (livemedia-creator)"
    if ! livemedia-creator --make-iso --no-virt \
        --ks /src/kickstart/jupiter-live.ks \
        --project "$DISTRO_NAME" \
        --releasever "$FEDORA_RELEASE" \
        --volid "$ISO_VOLID" \
        --resultdir /build/result \
        --tmp /var/tmp/lmc; then
        echo "error: livemedia-creator failed" >&2
        exit 1
    fi
}

if [[ "$STAGE" == "rpms" || "$STAGE" == "all" ]]; then
    build_rpms
fi
if [[ "$STAGE" == "iso" || "$STAGE" == "all" ]]; then
    validate_kickstart
    build_iso
fi
