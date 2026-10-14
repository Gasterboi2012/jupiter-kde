# Jupiter live ISO kickstart (KDE Plasma, minimal).
# Built by scripts/build-iso.sh via livemedia-creator. Edit this file to change
# what ships. Keep the package list KDE-native; the exceptions are
# gnome-disk-utility (kept on purpose) and helium-bin (the browser).

lang en_US.UTF-8
keyboard us
timezone UTC --utc
network --bootproto=dhcp --device=link --activate --onboot=yes
rootpw --lock
selinux --enforcing
firewall --enabled --service=mdns
services --enabled=NetworkManager,sddm,livesys,livesys-late

# Live image root filesystem size (MB).
part / --size=12288 --fstype=ext4
bootloader --timeout=1

# Fedora release and architecture are resolved by dnf inside the build chroot.
repo --name=fedora --metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-$releasever&arch=$basearch
repo --name=updates --metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f$releasever&arch=$basearch
# Helium browser (COPR imput/helium). Verify this baseurl against the COPR page before the first build.
repo --name=copr-helium --baseurl=https://download.copr.fedorainfracloud.org/results/imput/helium/fedora-$releasever-$basearch/
# Jupiter's own packages (branding + installer), built by scripts/build-iso.sh into the mounted repo.
repo --name=jupiter --baseurl=file:///jupiter-repo

%packages
# Base system and live-image support
@core
dracut-live
livesys-scripts
anaconda-live
dnf-plugins-core
NetworkManager-wifi
plymouth
plymouth-plugin-script
openssl

# KDE Plasma desktop (minimal)
sddm
plasma-desktop
plasma-workspace
plasma-nm
plasma-pa
plasma-systemmonitor
plasma-discover
powerdevil
kscreen
bluedevil
kinfocenter
google-noto-sans-fonts

# KDE-native applications
konsole
dolphin
kate
okular
gwenview
ark
spectacle
kcalc
partitionmanager
ffmpegthumbs
kdegraphics-thumbnailers
kio-extras

# Exception kept on purpose
gnome-disk-utility

# Browser
helium-bin

# Jupiter
fastfetch
jupiter-branding
jupiter-installer

# Keep the GNOME browser out if it is pulled in indirectly
-firefox
%end

%post --log=/root/jupiter-live-post.log
# Helium default browser comes from jupiter-branding's mimeapps.list.
# Keep the Helium COPR enabled on installed systems so it receives updates.
dnf -y copr enable imput/helium
# Boot splash: rebuild the live initramfs with the Jupiter theme.
plymouth-set-default-theme -R jupiter
%end
