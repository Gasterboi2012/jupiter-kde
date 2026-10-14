Name:           jupiter-installer
Version:        0.1.0
Release:        1%{?dist}
Summary:        Minimal text installer for Jupiter
License:        Apache-2.0
BuildArch:      noarch
URL:            https://github.com/Gasterboi2012/jupiter-kde
Source0:        jupiter-installer-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

Requires:       python3-textual
Requires:       NetworkManager
Requires:       util-linux
Requires:       openssl
Requires:       anaconda-live

%description
A small terminal UI that asks for network, install disk, user account, host
name and graphics driver, then runs the Fedora installer with a generated
kickstart. Start it with: sudo jupiter-installer

%prep
%autosetup -n jupiter-installer-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l jupiter_installer
install -Dpm0644 desktop/jupiter-installer.desktop \
    %{buildroot}%{_datadir}/applications/jupiter-installer.desktop

%check
%pytest

%files -f %{pyproject_files}
%{_datadir}/applications/jupiter-installer.desktop

%changelog
* Tue Oct 13 2026 Jupiter Maintainers <maintainers@jupiter.invalid> - 0.1.0-1
- Initial text installer
