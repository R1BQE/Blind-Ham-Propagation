from pathlib import Path


def test_updater_checks_geography_even_when_code_is_already_current():
    updater = Path(__file__).resolve().parents[1] / "scripts" / "bp"
    source = updater.read_text(encoding="utf-8")
    current_branch = source.index('if [[ "$current" == "$previous" ]]; then')
    next_update = source.index('if ! install_dependencies_if_changed', current_branch)
    current_path = source[current_branch:next_update]
    assert "ensure_geography.py" in current_path
    assert 'runuser -u "$SERVICE_USER"' in current_path
