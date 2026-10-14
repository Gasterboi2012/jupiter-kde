"""Jupiter text installer.

Flow: welcome -> network (skipped when wired) -> disk -> account -> hostname
-> graphics -> review -> install. Answers are validated per step and the
kickstart is only rendered once, at install time.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Log,
    OptionList,
    RadioButton,
    RadioSet,
    Static,
)
from textual.widgets.option_list import Option

from . import kickstart as ks
from . import system

VERSION = "0.1"
FLOW = ("welcome", "network", "disk", "account", "host", "gpu", "review")
PROGRESS_STEPS = ("network", "disk", "account", "host", "gpu", "review")
STEP_TITLES = {
    "network": "Network",
    "disk": "Install disk",
    "account": "User account",
    "host": "Host name",
    "gpu": "Graphics",
    "review": "Review",
}

BANNER = """\
      ╱╲
     ╱  ╲      J U P I T E R
    ╱ ◉  ╲     KDE Plasma · version {version}
    ╲    ╱
     ╲  ╱      (placeholder logo: replace branding later)
      ╲╱
"""


class StepScreen(Screen):
    """Base screen: progress line, body, error line and Back/Next buttons."""

    BINDINGS = [("escape", "back", "Back")]
    step: str = ""
    next_label: str = "Next"

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        if self.step in PROGRESS_STEPS:
            index = PROGRESS_STEPS.index(self.step) + 1
            yield Static(
                f"Step {index} of {len(PROGRESS_STEPS)} · {STEP_TITLES[self.step]}",
                classes="progress",
            )
        with Vertical(classes="panel"):
            yield from self.body()
            yield Static("", id="error", classes="error")
        with Horizontal(classes="nav"):
            yield Button("Back", id="back")
            yield Button(self.next_label, id="next", variant="primary")
        yield Footer()

    def body(self) -> ComposeResult:
        return iter(())

    def validate(self) -> None:
        """Raise ks.ValidationError to block navigation."""

    def collect(self) -> None:
        """Copy widget values into app.answers after validation."""

    def show_error(self, message: str) -> None:
        self.query_one("#error", Static).update(message)

    @on(Button.Pressed, "#back")
    def _on_back(self) -> None:
        self.app.go_back()

    @on(Button.Pressed, "#next")
    def _on_next(self) -> None:
        try:
            self.validate()
        except (ks.ValidationError, system.InstallerError) as exc:
            self.show_error(str(exc))
            return
        self.collect()
        self.app.go_next(self.step)

    def action_back(self) -> None:
        self.app.go_back()


class WelcomeScreen(StepScreen):
    step = "welcome"
    next_label = "Begin"

    def body(self) -> ComposeResult:
        yield Static(BANNER.format(version=VERSION), classes="banner")
        yield Static(
            "This installs Jupiter to a disk. You will choose a network (if needed), "
            "a disk, a user account, a host name and graphics drivers.\n\n"
            "Press Begin to continue."
        )


class NetworkScreen(StepScreen):
    step = "network"

    def __init__(self) -> None:
        super().__init__()
        self._networks: list[system.WifiNetwork] = []

    def body(self) -> ComposeResult:
        yield Static(
            "No wired connection found. Choose a Wi-Fi network, or continue offline.",
            id="net-status",
        )
        yield OptionList(id="wifi")
        yield Input(placeholder="Wi-Fi password (leave empty for open networks)", password=True, id="wifi-pass")
        with Horizontal(classes="nav"):
            yield Button("Scan", id="scan")
            yield Button("Connect", id="connect")

    def on_mount(self) -> None:
        self._scan()

    def _scan(self) -> None:
        try:
            self._networks = self.app.api.wifi_networks()
        except system.InstallerError as exc:
            self.show_error(f"Scan failed: {exc}")
            return
        options = self.query_one("#wifi", OptionList)
        options.clear_options()
        for index, net in enumerate(self._networks):
            options.add_option(Option(f"{net.ssid}   {net.signal}%   {net.security}", id=str(index)))

    @on(Button.Pressed, "#scan")
    def _on_scan(self) -> None:
        self._scan()

    @on(Button.Pressed, "#connect")
    def _on_connect(self) -> None:
        options = self.query_one("#wifi", OptionList)
        if options.highlighted is None or not self._networks:
            self.show_error("Select a network first.")
            return
        net = self._networks[options.highlighted]
        password = self.query_one("#wifi-pass", Input).value
        try:
            self.app.api.connect_wifi(net.ssid, password)
        except system.InstallerError as exc:
            self.show_error(f"Could not connect: {exc}")
            return
        self.query_one("#net-status", Static).update(f"Connected to {net.ssid}.")
        self.show_error("")


class DiskScreen(StepScreen):
    step = "disk"

    def __init__(self) -> None:
        super().__init__()
        self._disks: list[system.Disk] = []

    def body(self) -> ComposeResult:
        yield Static("Choose the disk to install Jupiter on.\n[b]All data on it will be erased.[/b]")
        yield OptionList(id="disks")

    def on_mount(self) -> None:
        try:
            self._disks = self.app.api.disks()
        except system.InstallerError as exc:
            self.show_error(f"Could not list disks: {exc}")
            return
        options = self.query_one("#disks", OptionList)
        for disk in self._disks:
            label = f"/dev/{disk.name}   {disk.size}   {disk.model or 'unknown model'}"
            options.add_option(Option(label, id=disk.name))

    def validate(self) -> None:
        if not self._disks:
            raise ks.ValidationError("No installable disks found.")
        if self.query_one("#disks", OptionList).highlighted is None:
            raise ks.ValidationError("Select a disk.")

    def collect(self) -> None:
        index = self.query_one("#disks", OptionList).highlighted
        self.app.answers.disk = self._disks[index].name


class AccountScreen(StepScreen):
    step = "account"

    def body(self) -> ComposeResult:
        yield Static("Create your user account. It gets sudo rights.")
        yield Input(placeholder="Username", id="user", value=self.app.answers.username)
        yield Input(placeholder="Password (min 8 characters)", password=True, id="pass")
        yield Input(placeholder="Repeat password", password=True, id="pass2")

    def validate(self) -> None:
        ks.validate_username(self.query_one("#user", Input).value)
        ks.validate_password(self.query_one("#pass", Input).value, self.query_one("#pass2", Input).value)

    def collect(self) -> None:
        self.app.answers.username = self.query_one("#user", Input).value.strip()
        self.app.answers.password = self.query_one("#pass", Input).value


class HostScreen(StepScreen):
    step = "host"

    def body(self) -> ComposeResult:
        yield Static("Name this computer on the network.")
        yield Input(value=self.app.answers.hostname, placeholder="jupiter", id="host")

    def validate(self) -> None:
        ks.validate_hostname(self.query_one("#host", Input).value)

    def collect(self) -> None:
        self.app.answers.hostname = ks.validate_hostname(self.query_one("#host", Input).value)


class GpuScreen(StepScreen):
    step = "gpu"

    def body(self) -> ComposeResult:
        yield Static("Which graphics hardware does this computer use?")
        with RadioSet(id="gpu"):
            for value, label in ks.GPU_CHOICES:
                yield RadioButton(label, value=value == self.app.answers.gpu)

    def validate(self) -> None:
        if self.query_one("#gpu", RadioSet).pressed_index < 0:
            raise ks.ValidationError("Choose a graphics option.")

    def collect(self) -> None:
        index = self.query_one("#gpu", RadioSet).pressed_index
        self.app.answers.gpu = ks.GPU_CHOICES[index][0]


class ReviewScreen(StepScreen):
    step = "review"
    next_label = "Install"

    def body(self) -> ComposeResult:
        yield Static("\n".join(self.app.answers.summary_lines()), classes="summary")
        yield Static("Press Install to start. Nothing is written before this point.")

    def validate(self) -> None:
        ks.validate_disk(self.app.answers.disk)
        ks.validate_username(self.app.answers.username)
        ks.validate_hostname(self.app.answers.hostname)


class InstallScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Installing Jupiter…", classes="progress", id="status")
        yield Log(id="log", auto_scroll=True)
        with Horizontal(classes="nav"):
            yield Button("Reboot", id="reboot", variant="success", disabled=True)
            yield Button("Exit", id="exit")
        yield Footer()

    def on_mount(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _emit(self, line: str) -> None:
        self.app.call_from_thread(self._write, line)

    def _write(self, line: str) -> None:
        self.query_one("#log", Log).write_line(line)

    def _run(self) -> None:
        app: JupiterInstaller = self.app  # type: ignore[assignment]
        try:
            text = ks.render_kickstart(app.answers, ks.hash_password(app.answers.password))
            code = system.run_install(text, dry_run=app.dry_run, emit=self._emit)
        except (ks.ValidationError, system.InstallerError, OSError, subprocess.CalledProcessError) as exc:
            self._emit(f"Error: {exc}")
            code = 1
        self.app.call_from_thread(self._finish, code)

    def _finish(self, code: int) -> None:
        if self.app.dry_run:
            message = "Dry run finished. Nothing was installed."
        elif code == 0:
            message = "Installed. Remove the USB stick and reboot."
        else:
            message = f"Installer failed (exit {code})."
        self.query_one("#status", Static).update(message)
        # Reboot only after a real, successful install.
        self.query_one("#reboot", Button).disabled = self.app.dry_run or code != 0

    @on(Button.Pressed, "#reboot")
    def _reboot(self) -> None:
        os.system("systemctl reboot")

    @on(Button.Pressed, "#exit")
    def _exit(self) -> None:
        self.app.exit(0)


SCREENS: dict[str, type[StepScreen]] = {
    "welcome": WelcomeScreen,
    "network": NetworkScreen,
    "disk": DiskScreen,
    "account": AccountScreen,
    "host": HostScreen,
    "gpu": GpuScreen,
    "review": ReviewScreen,
}


class JupiterInstaller(App):
    CSS_PATH = "jupiter.tcss"
    TITLE = "Jupiter Installer"

    def __init__(self, api=None, dry_run: bool = False) -> None:
        super().__init__()
        self.api = api or system.SystemAPI()
        self.dry_run = dry_run
        self.answers = ks.Answers()
        self._history: list[str] = []
        self._current = "welcome"

    def on_mount(self) -> None:
        self._show("welcome")

    def _show(self, name: str) -> None:
        self._current = name
        screen = InstallScreen() if name == "install" else SCREENS[name]()
        # The default screen cannot be switched away from, so the first step is pushed.
        if len(self.screen_stack) > 1:
            self.switch_screen(screen)
        else:
            self.push_screen(screen)

    def _next_after(self, name: str) -> str:
        index = FLOW.index(name) + 1
        if index >= len(FLOW):
            return "install"
        nxt = FLOW[index]
        if nxt == "network" and self.api.has_wired_connection():
            return self._next_after(nxt)
        return nxt

    def go_next(self, current: str) -> None:
        target = self._next_after(current)
        self._history.append(current)
        self._show(target)

    def go_back(self) -> None:
        if not self._history:
            return
        self._show(self._history.pop())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jupiter-installer", description="Install Jupiter.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect answers and write the kickstart, but do not start the installer.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if os.geteuid() != 0 and not args.dry_run:
        print("jupiter-installer must run as root: sudo jupiter-installer", file=sys.stderr)
        return 1
    JupiterInstaller(dry_run=args.dry_run).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
