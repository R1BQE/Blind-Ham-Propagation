from pathlib import Path


def test_vds_installer_builds_and_validates_geography_before_starting_service():
    installer = Path(__file__).resolve().parents[1] / "scripts" / "install_vds.sh"
    source = installer.read_text(encoding="utf-8")

    build_position = source.index('scripts/build_geography.py')
    integrity_position = source.index('PRAGMA quick_check')
    service_start_position = source.index('systemctl restart "${SERVICE_NAME}.service"')

    assert build_position < integrity_position < service_start_position
    assert 'if [[ ! -s "${GEOGRAPHY_DB}" ]]' in source
    assert 'database_schema' in source
    assert 'runuser -u "${SERVICE_USER}"' in source
