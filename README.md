# Jupiter

Jupiter is a minimal Fedora-based distribution with a KDE Plasma desktop.
Version **0.1**. It is built from this repository.

## What ships

- **Desktop:** KDE Plasma (SDDM login), minimal set of KDE-native apps:
  Dolphin, Konsole, Kate, Okular, Gwenview, Ark, Spectacle, KCalc,
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

Requirements: a Linux host with `sudo` and `podman`, and network access.

```sh
make test     # installer and config tests (no Fedora needed)
make rpms     # build jupiter-branding and jupiter-installer RPMs -> build/repo
make iso      # build the live ISO -> build/result/jupiter-0.1-x86_64.iso
make clean
```

The build runs in a `fedora:<FEDORA_RELEASE>` container. It uses `livemedia-creator`
(package `lorax-lmc-novirt`) with `--no-virt`. Test the ISO in a VM before you
distribute it.

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
