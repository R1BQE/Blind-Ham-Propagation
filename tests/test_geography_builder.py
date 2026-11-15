import sqlite3
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_geography import import_russian_alternate_names


def test_import_russian_alternate_names_prefers_preferred_variant(tmp_path):
    archive_path = tmp_path / "alternateNamesV2.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "alternateNamesV2.txt",
            "1\t123\tru\tМосква (вариант)\t0\n"
            "2\t123\tru\tМосква\t1\n"
            "3\t456\ten\tMoscow\t1\n",
        )

    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE settlements (geoname_id INTEGER PRIMARY KEY, name_ru TEXT)"
    )
    connection.executemany(
        "INSERT INTO settlements(geoname_id) VALUES (?)",
        [(123,), (456,), (789,)],
    )

    matched = import_russian_alternate_names(archive_path, connection)

    assert matched == 1
    assert connection.execute(
        "SELECT name_ru FROM settlements WHERE geoname_id = 123"
    ).fetchone()[0] == "Москва"
    assert connection.execute(
        "SELECT name_ru FROM settlements WHERE geoname_id = 456"
    ).fetchone()[0] is None
    connection.close()
