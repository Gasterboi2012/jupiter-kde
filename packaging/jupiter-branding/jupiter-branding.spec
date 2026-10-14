Name:           jupiter-branding
Version:        0.1
Release:        1%{?dist}
Summary:        Jupiter branding: logo, Info Center identity, fastfetch and boot splash
License:        Apache-2.0
BuildArch:      noarch
URL:            https://github.com/Gasterboi2012/jupiter-kde
Source0:        jupiter-branding-%{version}.tar.gz

Requires:       plymouth
Requires:       plymouth-plugin-script
Requires:       fastfetch
Requires:       kinfocenter
Requires:       fedora-release

%description
Placeholder branding for the Jupiter distribution. Replace the files in the
package sources (logo, splash image, fastfetch logo) with final artwork.

%prep
%setup -q -n jupiter-branding-%{version}

%build

%install
install -Dpm0644 icons/hicolor/scalable/apps/jupiter-logo.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/jupiter-logo.svg
install -Dpm0644 kcm/kcm-about-distrorc \
    %{buildroot}%{_sysconfdir}/xdg/kcm-about-distrorc
install -Dpm0644 fastfetch/config.jsonc \
    %{buildroot}%{_sysconfdir}/xdg/fastfetch/config.jsonc
install -Dpm0644 fastfetch/ascii.txt \
    %{buildroot}%{_datadir}/jupiter/branding/ascii.txt
install -Dpm0644 mimeapps.list \
    %{buildroot}%{_sysconfdir}/xdg/mimeapps.list
install -Dpm0644 plymouth/jupiter/jupiter.plymouth \
    %{buildroot}%{_datadir}/plymouth/themes/jupiter/jupiter.plymouth
install -Dpm0644 plymouth/jupiter/jupiter.script \
    %{buildroot}%{_datadir}/plymouth/themes/jupiter/jupiter.script
install -Dpm0644 plymouth/jupiter/logo.png \
    %{buildroot}%{_datadir}/plymouth/themes/jupiter/logo.png

%post
# Identify the system as Jupiter. ID stays "fedora" so Fedora tooling and
# repositories keep working. Idempotent: old Jupiter lines are replaced.
if [ -f /usr/lib/os-release ]; then
    sed -i -e '/^\(NAME\|PRETTY_NAME\|VARIANT\|VARIANT_ID\|LOGO\)=/d' /usr/lib/os-release
    cat >> /usr/lib/os-release <<'EOF'
NAME="Jupiter"
PRETTY_NAME="Jupiter 0.1 (KDE Plasma)"
VARIANT="KDE Plasma"
VARIANT_ID=kde
LOGO=jupiter-logo
EOF
fi
# Make Jupiter the default plymouth theme (initramfs is rebuilt by the installer/build).
plymouth-set-default-theme jupiter >/dev/null 2>&1 || :

%files
%{_datadir}/icons/hicolor/scalable/apps/jupiter-logo.svg
%config(noreplace) %{_sysconfdir}/xdg/kcm-about-distrorc
%config(noreplace) %{_sysconfdir}/xdg/fastfetch/config.jsonc
%config(noreplace) %{_sysconfdir}/xdg/mimeapps.list
%{_datadir}/jupiter/branding/ascii.txt
%{_datadir}/plymouth/themes/jupiter/

%changelog
* Tue Oct 13 2026 Jupiter Maintainers <maintainers@jupiter.invalid> - 0.1-1
- Initial placeholder branding package
