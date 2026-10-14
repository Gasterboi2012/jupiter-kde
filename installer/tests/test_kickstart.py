import pytest

from jupiter_installer import kickstart as ks
from jupiter_installer import system


def answers(**overrides):
    base = dict(hostname="jupiter-box", username="alice", password="correct horse", disk="sda", gpu=ks.GPU_DEFAULT)
    base.update(overrides)
    return ks.Answers(**base)


HASH = "$6$saltsalt$abcdefghijklmnopqrstuvwxyz"


def test_render_contains_answers_and_no_plaintext_password():
    text = ks.render_kickstart(answers(), HASH)
    assert "network --bootproto=dhcp --device=link --activate --onboot=yes --hostname=jupiter-box" in text
    assert "ignoredisk --only-use=sda" in text
    assert "clearpart --all --initlabel --drives=sda" in text
    assert f"user --name=alice --groups=wheel --iscrypted --password={HASH}" in text
    assert "correct horse" not in text


def test_default_gpu_has_no_nvidia_section():
    assert "akmod-nvidia-open" not in ks.render_kickstart(answers(gpu=ks.GPU_DEFAULT), HASH)


def test_nvidia_choice_installs_nvidia_open_from_rpmfusion():
    text = ks.render_kickstart(answers(gpu=ks.GPU_NVIDIA), HASH)
    assert "dnf -y install akmod-nvidia-open" in text
    assert "rpmfusion-nonfree-release" in text
    assert "nvidia-drm.modeset=1" in text
    assert "kmod-nvidia\n" not in text and "akmod-nvidia " not in text


def test_install_enables_plasma_login_manager():
    text = ks.render_kickstart(answers(), HASH)
    assert "services --enabled=NetworkManager,plasmalogin" in text
    assert "sddm" not in text


def test_plymouth_theme_is_set_in_every_install():
    assert "plymouth-set-default-theme -R jupiter" in ks.render_kickstart(answers(), HASH)


@pytest.mark.parametrize("name", ["alice", "_svc", "bob-2"])
def test_valid_usernames(name):
    assert ks.validate_username(name) == name


@pytest.mark.parametrize("name", ["", "Alice", "1bob", "a b", "x" * 33, "root;rm"])
def test_invalid_usernames(name):
    with pytest.raises(ks.ValidationError):
        ks.validate_username(name)


@pytest.mark.parametrize("name", ["jupiter", "my-pc", "PC01"])
def test_valid_hostnames(name):
    assert ks.validate_hostname(name) == name.lower()


@pytest.mark.parametrize("name", ["", "-lead", "trail-", "a.b", "x" * 64, "bad_name"])
def test_invalid_hostnames(name):
    with pytest.raises(ks.ValidationError):
        ks.validate_hostname(name)


def test_password_rules():
    ks.validate_password("longenough", "longenough")
    with pytest.raises(ks.ValidationError):
        ks.validate_password("short", "short")
    with pytest.raises(ks.ValidationError):
        ks.validate_password("longenough", "different1")


def test_render_rejects_bad_disk_and_gpu():
    with pytest.raises(ks.ValidationError):
        ks.render_kickstart(answers(disk="sda; rm -rf /"), HASH)
    with pytest.raises(ks.ValidationError):
        ks.render_kickstart(answers(gpu="radeon-magic"), HASH)


def test_render_rejects_non_sha512_hash():
    with pytest.raises(ks.ValidationError):
        ks.render_kickstart(answers(), "plaintext")


def test_hash_password_produces_sha512_crypt():
    digest = ks.hash_password("correct horse")
    assert digest.startswith("$6$")
    assert "correct horse" not in digest


# ---- system parsers ----

def test_wired_detection():
    out = "wifi:disconnected\nethernet:connected\nloopback:unmanaged\n"
    assert system.has_wired_connection(out)
    assert not system.has_wired_connection("wifi:connected\nethernet:unavailable\n")


def test_wifi_list_parses_escaped_colons_and_dedupes():
    out = "Home\\:5G:80:WPA2\nHome\\:5G:40:WPA2\nCafe:55:\n:70:WPA\n"
    nets = system.parse_wifi_list(out)
    assert [n.ssid for n in nets] == ["Home:5G", "Cafe"]
    assert nets[0].signal == "80"
    assert nets[1].security == "open"


def test_parse_disks_skips_optical_and_loop():
    data = '{"blockdevices":[{"name":"sda","size":"500G","model":"SSD ","type":"disk"},' \
           '{"name":"sr0","size":"1G","model":"DVD","type":"rom"},' \
           '{"name":"loop0","size":"1G","model":null,"type":"loop"},' \
           '{"name":"nvme0n1","size":"1T","model":"NVMe","type":"disk"}]}'
    disks = system.parse_disks(data)
    assert [d.name for d in disks] == ["sda", "nvme0n1"]
    assert disks[0].model == "SSD"


def test_dry_run_writes_private_kickstart_without_installing(tmp_path, monkeypatch):
    monkeypatch.setattr(system.tempfile, "tempdir", str(tmp_path))
    lines = []
    code = system.run_install("lang en_US.UTF-8\n", dry_run=True, emit=lines.append)
    assert code == 0
    path = next(line.split("written to ")[1] for line in lines if "written to" in line)
    import os, stat
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert open(path).read() == "lang en_US.UTF-8\n"
    assert any("Dry run" in line for line in lines)
