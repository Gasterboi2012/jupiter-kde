from textual.widgets import Button, Input, OptionList, RadioSet, Static

from jupiter_installer import kickstart as ks
from jupiter_installer import system
from jupiter_installer.app import JupiterInstaller


class FakeAPI:
    def __init__(self, wired=False):
        self.wired = wired
        self.connected = []

    def has_wired_connection(self):
        return self.wired

    def wifi_networks(self):
        return [system.WifiNetwork("Home", "80", "WPA2")]

    def connect_wifi(self, ssid, password):
        self.connected.append((ssid, password))

    def disks(self):
        return [system.Disk("sda", "500G", "SSD")]


async def click(pilot, selector):
    await pilot.click(selector)
    await pilot.pause()


async def test_wired_machine_skips_network_step():
    app = JupiterInstaller(api=FakeAPI(wired=True), dry_run=True)
    async with app.run_test() as pilot:
        await click(pilot, "#next")  # welcome -> disk (network skipped)
        assert app.screen.step == "disk"


async def test_full_flow_wifi_then_nvidia_dry_run():
    api = FakeAPI(wired=False)
    app = JupiterInstaller(api=api, dry_run=True)
    async with app.run_test(size=(120, 60)) as pilot:
        await click(pilot, "#next")  # welcome -> network
        assert app.screen.step == "network"
        app.screen.query_one("#wifi", OptionList).highlighted = 0
        app.screen.query_one("#wifi-pass", Input).value = "wifipass"
        await click(pilot, "#connect")
        assert api.connected == [("Home", "wifipass")]
        await click(pilot, "#next")  # network -> disk
        assert app.screen.step == "disk"
        app.screen.query_one("#disks", OptionList).highlighted = 0
        await click(pilot, "#next")
        assert app.screen.step == "account"
        app.screen.query_one("#user", Input).value = "alice"
        app.screen.query_one("#pass", Input).value = "correct horse"
        app.screen.query_one("#pass2", Input).value = "correct horse"
        await click(pilot, "#next")
        assert app.screen.step == "host"
        app.screen.query_one("#host", Input).value = "jupiter-box"
        await click(pilot, "#next")
        assert app.screen.step == "gpu"
        await click(pilot, app.screen.query("#gpu RadioButton")[1])
        await click(pilot, "#next")
        assert app.screen.step == "review"
        assert app.answers.disk == "sda"
        assert app.answers.username == "alice"
        assert app.answers.hostname == "jupiter-box"
        assert app.answers.gpu == ks.GPU_NVIDIA
        assert "correct horse" not in "\n".join(app.answers.summary_lines())
        await click(pilot, "#next")  # install (dry run)
        await pilot.pause(0.5)
        status = str(app.screen.query_one("#status", Static).render())
        assert "Dry run finished" in status
        assert app.screen.query_one("#reboot", Button).disabled


async def test_account_validation_blocks_navigation():
    app = JupiterInstaller(api=FakeAPI(wired=True), dry_run=True)
    async with app.run_test() as pilot:
        await click(pilot, "#next")  # -> disk
        app.screen.query_one("#disks", OptionList).highlighted = 0
        await click(pilot, "#next")  # -> account
        assert app.screen.step == "account"
        app.screen.query_one("#user", Input).value = "Bad Name"
        app.screen.query_one("#pass", Input).value = "correct horse"
        app.screen.query_one("#pass2", Input).value = "correct horse"
        await click(pilot, "#next")
        assert app.screen.step == "account"
        error = str(app.screen.query_one("#error", Static).render())
        assert "Username" in error


async def test_back_returns_to_previous_step():
    app = JupiterInstaller(api=FakeAPI(wired=True), dry_run=True)
    async with app.run_test() as pilot:
        await click(pilot, "#next")
        assert app.screen.step == "disk"
        await click(pilot, "#back")
        assert app.screen.step == "welcome"
