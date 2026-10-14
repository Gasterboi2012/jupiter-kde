"""Validate Jupiter's configuration files without needing a Fedora host."""

import configparser
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "packaging/jupiter-branding/files"
KS = ROOT / "kickstart/jupiter-live.ks"


def strip_full_line_jsonc_comments(text: str) -> str:
    # fastfetch config uses only full-line // comments; keep "//" inside URLs intact.
    return "\n".join(line for line in text.splitlines() if not re.match(r"^\s*//", line))


def packages_section() -> list[str]:
    text = KS.read_text()
    body = text.split("%packages", 1)[1].split("%end", 1)[0]
    return [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]


def test_distro_conf_has_name_version_and_release():
    values = dict(
        line.split("=", 1) for line in (ROOT / "distro.conf").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert values["DISTRO_NAME"] == "Jupiter"
    assert values["DISTRO_VERSION"] == "0.1"
    assert values["FEDORA_RELEASE"] == "44"


def test_fastfetch_config_is_valid_jsonc_and_minimal():
    data = json.loads(strip_full_line_jsonc_comments((BRAND / "fastfetch/config.jsonc").read_text()))
    assert data["logo"]["source"] == "/usr/share/jupiter/branding/ascii.txt"
    names = [m if isinstance(m, str) else m["type"] for m in data["modules"]]
    assert "os" in names and "de" in names
    assert len(names) <= 16, "config should stay minimal"


def test_kcm_info_center_shows_jupiter_name_version_and_logo():
    cp = configparser.ConfigParser()
    cp.read(BRAND / "kcm/kcm-about-distrorc")
    assert cp["General"]["Name"] == "Jupiter"
    assert cp["General"]["Version"] == "0.1"
    logo = cp["General"]["LogoPath"]
    assert (BRAND / "icons/hicolor/scalable/apps/jupiter-logo.svg").exists()
    assert logo == "/usr/share/icons/hicolor/scalable/apps/jupiter-logo.svg"


def test_plymouth_theme_files_are_consistent():
    theme = BRAND / "plymouth/jupiter"
    cp = configparser.ConfigParser()
    cp.read(theme / "jupiter.plymouth")
    assert cp["Plymouth Theme"]["ModuleName"] == "script"
    assert cp["script"]["ScriptFile"].endswith("/jupiter.script")
    assert "logo.png" in (theme / "jupiter.script").read_text()
    png = (theme / "logo.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_branding_spec_installs_every_source_file_it_ships():
    spec = (ROOT / "packaging/jupiter-branding/jupiter-branding.spec").read_text()
    for path in [
        "icons/hicolor/scalable/apps/jupiter-logo.svg",
        "kcm/kcm-about-distrorc",
        "fastfetch/config.jsonc",
        "fastfetch/ascii.txt",
        "mimeapps.list",
        "plymouth/jupiter/jupiter.plymouth",
        "plymouth/jupiter/jupiter.script",
        "plymouth/jupiter/logo.png",
    ]:
        assert path in spec, path
        assert (BRAND / path).exists(), path


def test_package_policy_is_kde_native_with_gnome_disk_utility_exception():
    pkgs = packages_section()
    assert "plasma-desktop" in pkgs and "sddm" in pkgs
    gnome = [p for p in pkgs if p.startswith("gnome") and p != "gnome-disk-utility"]
    assert gnome == [], f"unexpected GNOME packages: {gnome}"
    assert "gnome-disk-utility" in pkgs
    assert "helium-bin" in pkgs
    assert "-firefox" in pkgs
    assert "firefox" not in [p for p in pkgs if not p.startswith("-")]


def test_live_kickstart_ships_jupiter_packages_and_repos():
    text = KS.read_text()
    for pkg in ["jupiter-branding", "jupiter-installer", "fastfetch"]:
        assert pkg in packages_section()
    assert "file:///jupiter-repo" in text
    assert "copr.fedorainfracloud.org/results/imput/helium" in text


@pytest.mark.parametrize("ks_text_source", ["live", "installer"])
def test_kickstart_passes_pykickstart(ks_text_source, tmp_path):
    pykickstart = pytest.importorskip("pykickstart.parser")
    from pykickstart.version import makeVersion

    if ks_text_source == "live":
        text = KS.read_text()
    else:
        sys.path.insert(0, str(ROOT / "installer"))
        from jupiter_installer import kickstart as ks

        text = ks.render_kickstart(
            ks.Answers(hostname="jupiter-box", username="alice", password="x" * 9, disk="sda", gpu=ks.GPU_NVIDIA),
            "$6$saltsalt$abcdefghijklmnopqrstuvwxyz",
        )
    handler = makeVersion()
    parser = pykickstart.KickstartParser(handler, errorsAreFatal=True, missingIncludeIsFatal=False)
    path = tmp_path / "ks.cfg"
    path.write_text(text)
    parser.readKickstart(str(path))
