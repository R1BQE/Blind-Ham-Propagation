from pathlib import Path


def test_vds_installer_uses_shared_geography_preparation_before_starting_service():
    root = Path(__file__).resolve().parents[1]
    installer = (root / "scripts" / "install_vds.sh").read_text(encoding="utf-8")
    prepare_position = installer.index("scripts/ensure_geography.py")
    service_start_position = installer.index('systemctl restart "${SERVICE_NAME}.service"')
    assert prepare_position < service_start_position
    assert 'runuser -u "${SERVICE_USER}"' in installer
