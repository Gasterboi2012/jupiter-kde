"""System access for the Jupiter installer.

Parsers are pure functions so they can be tested without NetworkManager.
``SystemAPI`` wraps the real commands; the TUI accepts any object with the
same methods, which is how the tests inject fakes.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass

# Anaconda is the Fedora installer. Override with JUPITER_INSTALL_COMMAND
# (shell-quoted) if the live environment wraps it differently.
DEFAULT_INSTALL_COMMAND = ("anaconda", "--text", "--kickstart")


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    signal: str
    security: str


@dataclass(frozen=True)
class Disk:
    name: str
    size: str
    model: str


class InstallerError(RuntimeError):
    pass


# ---------- pure parsers ----------

def split_nmcli_terse(line: str) -> list[str]:
    """Split a ``nmcli -t`` line on unescaped ':' and unescape ``\\:``."""
    fields = re.split(r"(?<!\\):", line.rstrip("\n"))
    return [f.replace("\\:", ":").replace("\\\\", "\\") for f in fields]


def has_wired_connection(device_status: str) -> bool:
    """True if ``nmcli -t -f TYPE,STATE device`` reports a connected ethernet device."""
    for line in device_status.splitlines():
        fields = split_nmcli_terse(line)
        if len(fields) >= 2 and fields[0] == "ethernet" and fields[1] == "connected":
            return True
    return False


def parse_wifi_list(output: str) -> list[WifiNetwork]:
    """Parse ``nmcli -t -f SSID,SIGNAL,SECURITY device wifi list``."""
    networks: dict[str, WifiNetwork] = {}
    for line in output.splitlines():
        fields = split_nmcli_terse(line)
        if len(fields) < 3 or not fields[0]:
            continue
        ssid, signal, security = fields[0], fields[1], fields[2] or "open"
        # Keep the strongest entry per SSID (nmcli lists each AP separately).
        previous = networks.get(ssid)
        if previous is None or _as_int(signal) > _as_int(previous.signal):
            networks[ssid] = WifiNetwork(ssid, signal, security)
    return sorted(networks.values(), key=lambda n: -_as_int(n.signal))


def _as_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return -1


def parse_disks(lsblk_json: str) -> list[Disk]:
    """Parse ``lsblk -J -d -o NAME,SIZE,MODEL,TYPE`` and keep real disks only."""
    data = json.loads(lsblk_json)
    disks: list[Disk] = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue
        name = dev.get("name") or ""
        if not name or name.startswith(("loop", "sr", "zram", "rbd")):
            continue
        disks.append(Disk(name, dev.get("size") or "?", (dev.get("model") or "").strip()))
    return disks


# ---------- real system calls ----------

def _run(cmd: list[str], *, input_text: str | None = None, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            cmd, input=input_text, text=True, capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallerError(f"{cmd[0]}: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
        raise InstallerError(f"{' '.join(cmd[:2])} failed: {message}")
    return result.stdout


class SystemAPI:
    """Real implementation used on the live system."""

    def has_wired_connection(self) -> bool:
        if shutil.which("nmcli") is None:
            return False
        try:
            return has_wired_connection(_run(["nmcli", "-t", "-f", "TYPE,STATE", "device"]))
        except InstallerError:
            return False

    def wifi_networks(self) -> list[WifiNetwork]:
        _run(["nmcli", "device", "wifi", "rescan"], timeout=20)
        return parse_wifi_list(
            _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
        )

    def connect_wifi(self, ssid: str, password: str) -> None:
        cmd = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            cmd += ["password", password]
        _run(cmd, timeout=90)

    def disks(self) -> list[Disk]:
        return parse_disks(_run(["lsblk", "-J", "-d", "-o", "NAME,SIZE,MODEL,TYPE"]))


def install_command() -> list[str]:
    override = os.environ.get("JUPITER_INSTALL_COMMAND")
    return shlex.split(override) if override else list(DEFAULT_INSTALL_COMMAND)


def write_kickstart(text: str) -> str:
    """Write the kickstart to a private temp dir (mode 0600) and return its path."""
    directory = tempfile.mkdtemp(prefix="jupiter-")
    path = os.path.join(directory, "jupiter-install.ks")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
    return path


def run_install(
    kickstart_text: str, *, dry_run: bool, emit: Callable[[str], None]
) -> int:
    """Run the installer with the kickstart, streaming output through ``emit``."""
    path = write_kickstart(kickstart_text)
    emit(f"Kickstart written to {path}")
    if dry_run:
        emit("Dry run: installer not started.")
        return 0
    cmd = [*install_command(), path]
    emit("$ " + " ".join(shlex.quote(part) for part in cmd))
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
    except OSError as exc:
        emit(f"Could not start installer: {exc}")
        return 127
    assert proc.stdout is not None
    for line in proc.stdout:
        emit(line.rstrip())
    return proc.wait()
