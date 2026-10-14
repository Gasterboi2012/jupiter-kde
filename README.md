# Jupiter

Jupiter is a minimal Fedora-based distribution with a KDE Plasma desktop.
Version **0.1**. It is built from this repository.

## What ships

- **Desktop:** KDE Plasma (Plasma Login Manager), minimal set of KDE-native apps:
  Dolphin, Konsole, Kate, Gwenview, Ark, Spectacle,
  KDE Partition Manager, Discover, System Monitor, Info Center.
- **Exception:** `gnome-disk-utility` is included on purpose.
- **Browser:** Helium (`helium-bin` from the `imput/helium` COPR), set as default.
- **Branding placeholders** (replace later):
  - Logo: `packaging/jupiter-branding/files/icons/hicolor/scalable/apps/jupiter-logo.svg`
  - Info Center name/version/logo: `packaging/jupiter-branding/files/kcm/kcm-about-distrorc`
  - fastfetch config and text logo: `packaging/jupiter-branding/files/fastfetch/`
  - Boot splash: `packaging/jupiter-branding/files/plymouth/jupiter/` (`logo.png`, `jupiter.script`)
- **Installer:** `jupiter-installer`, a terminal UI (`installer/`). It asks for:
  network (skipped when a wired connection is present), install disk,
  user account, host name, and graphics (default drivers or NVIDIA via `akmod-nvidia-open`).

## Repository layout

| Path | Purpose |
| --- | --- |
| `distro.conf` | Name, version, Fedora release and ISO volume label |
| `kickstart/jupiter-live.ks` | Live ISO definition: packages, repos, services |
| `packaging/jupiter-branding/` | RPM: logo, Info Center, fastfetch, plymouth, os-release identity |
| `packaging/jupiter-installer/` | RPM spec for the installer |
| `installer/` | Installer source (Python + Textual), tests, desktop launcher |
| `scripts/build-iso.sh` | Host entry point: runs the Fedora builder container |
| `scripts/container-build.sh` | Inside the container: builds RPMs, validates kickstart, runs livemedia-creator |
| `scripts/generate-placeholders.py` | Regenerates the placeholder splash PNG |
| `tests/` | Config and kickstart validation tests |

## Customising

1. Replace the placeholder art (keep the file names):
   - `jupiter-logo.svg` (icon used by Info Center and the launcher)
   - `plymouth/jupiter/logo.png` (≈512×512, transparent background)
   - `fastfetch/ascii.txt` (or point `logo.source` at an image)
2. Change the name or version in `packaging/jupiter-branding/files/kcm/kcm-about-distrorc`.
   The os-release name is set in `packaging/jupiter-branding/jupiter-branding.spec`.
3. Add or remove packages in the `%packages` section of `kickstart/jupiter-live.ks`.
4. Change the version or Fedora release in `distro.conf`. Keep the tarball
   names in `scripts/container-build.sh` in sync with the spec `Version:` fields.

## Building

### Requirements

- A Linux host with `podman` and `sudo` (the ISO step runs privileged).
- Network access (the container pulls `registry.fedoraproject.org/fedora:<FEDORA_RELEASE>`
  and downloads packages from the Fedora, RPM Fusion and COPR mirrors).
- Free disk space: the live root is 12 GB and the build needs scratch space on top of it.
  Plan for tens of GB free.
- `make` (GNU make). Python 3 with `pytest`, `pytest-asyncio` and `textual` is only needed for `make test`.

Install the host tools on Fedora:

```sh
sudo dnf install -y podman make python3-pytest python3-pytest-asyncio python3-textual
```

### Step by step

Run all commands from the repository root.

1. **Run the tests** (no Fedora or podman needed):

   ```sh
   make test
   ```

   Expect `35 passed` for the installer and `10 passed` for the config checks.
   Stop if anything fails.

2. **Build the RPMs** (fast check of the packaging):

   ```sh
   make rpms
   ```

   This runs `scripts/build-iso.sh rpms` and builds `jupiter-branding` and
   `jupiter-installer` inside the Fedora container. The RPMs are copied to
   `build/repo/` and indexed there with `createrepo_c`. The kickstart reads them
   from that directory through `file:///jupiter-repo`.

3. **Build the live ISO**:

   ```sh
   make iso
   ```

   This runs `scripts/build-iso.sh all`, which does step 2 again and then:
   - validates `kickstart/jupiter-live.ks` with `ksvalidator` for `F<FEDORA_RELEASE>`
     (a bad kickstart fails here, before any image is built), then
   - runs `livemedia-creator --make-iso --no-virt` to install the kickstart into a
     chroot and produce the live image.

   Output: `build/result/jupiter-0.1-x86_64.iso`. The script prints `ISO: <path>`
   when it succeeds and exits non-zero if no ISO was produced.

4. **Check the result**: the ISO is the last line printed. Confirm the file exists:

   ```sh
   ls -lh build/result/jupiter-0.1-x86_64.iso
   ```

### Build options

- **Rootful podman without sudo**: if your user runs podman as root already, skip the
  sudo wrapper: `PODMAN=podman make iso` (set the variable in the environment).
- **Rebuild after changes**: `make rpms` rebuilds the two RPMs from the current source.
  `make iso` always rebuilds the RPMs first, then the ISO. To start clean, run
  `make clean` (it removes `build/`, including the RPM repo and previous ISOs).
- **Change the release**: edit `FEDORA_RELEASE` in `distro.conf`. The container image,
  `ksvalidator` and `livemedia-creator --releasever` all follow it.

### Where things go

| Path | Contents |
| --- | --- |
| `build/repo/` | Built RPMs plus repo metadata (mounted into the container as `/jupiter-repo`) |
| `build/result/` | `livemedia-creator` output; the final ISO is `jupiter-<version>-x86_64.iso` |
| `build/` | Everything above. Git ignores it. |

Inside the container, `livemedia-creator` writes its temporary files to `/var/tmp/lmc`.
This is in the container, not in `build/`.

### Troubleshooting

- **`ksvalidator` error**: the message names the line in `kickstart/jupiter-live.ks`.
  Fix that line and rerun `make iso`.
- **`dnf builddep` or `rpmbuild` error**: the failing spec is named in the output.
  Run `make rpms` again after fixing the spec or the source tarball contents.
- **Helium packages not found**: the COPR `baseurl` in the kickstart is unverified.
  Check the `imput/helium` COPR page for the correct Fedora 44 repo URL.
- **Failed `%post` in the live image**: the log is in the image at `/root/jupiter-live-post.log`.
- **No ISO produced**: check the `livemedia-creator` output above the error. The
  `livemedia-creator` flags are from its documentation and have not been run against
  this kickstart.

### Test the ISO

Boot the ISO in a VM before you distribute it. Example with QEMU and KVM:

```sh
qemu-system-x86_64 -enable-kvm -m 4096 -smp 2 -cdrom build/result/jupiter-0.1-x86_64.iso
```

For the installer, use a VM disk (for example `qemu-img create -f qcow2 disk.qcow2 40G`)
so the erase step runs against the disk you intend to test.

## Installing

1. Boot the ISO. Log in as `liveuser` (KDE live session).
2. Start **Install Jupiter** from the application menu, or run `sudo jupiter-installer`.
3. Follow the steps. Choosing a disk erases it.

Developers can run the installer without changing the disk:
`jupiter-installer --dry-run` writes the kickstart to a temp file and stops.

## Status and known limits

- The installer invokes Anaconda with `anaconda --text --kickstart <file>` by default.
  Override this with `JUPITER_INSTALL_COMMAND` if your live environment needs a
  different invocation. This path is not yet verified on real hardware.
- Replacement artwork is placeholder only.
- The Helium COPR `baseurl` in the kickstart should be checked against the COPR page before the first build.
