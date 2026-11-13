"""Static safety-contract tests for the production VDS updater."""

from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bp"
SOURCE = SCRIPT.read_text(encoding="utf-8")


def test_updater_rejects_untracked_worktree_files() -> None:
    assert "status --porcelain --untracked-files=all" in SOURCE
    assert "Рабочая копия содержит изменения или незатреканные файлы" in SOURCE


def test_rollback_requires_verified_git_reset_and_health() -> None:
    rollback = SOURCE.split("rollback_transaction() {", 1)[1].split("do_update() {", 1)[0]
    assert 'git -C "$ROOT" reset --hard "$previous"' in rollback
    assert 'actual="$(git -C "$ROOT" rev-parse HEAD' in rollback
    assert 'restore_configs "$work" || failed=1' in rollback
    assert 'systemctl restart "$SERVICE" || failed=1' in rollback
    assert "Откат подтверждён" in rollback
    assert "откат НЕ подтверждён" in rollback


def test_config_restore_checks_the_restored_files() -> None:
    restore = SOURCE.split("restore_configs() {", 1)[1].split("save_config_backups() {", 1)[0]
    assert 'cmp -s "$work/unit.before" "$SERVICE_FILE"' in restore
    assert 'cmp -s "$work/apache.before" "$APACHE_FILE"' in restore
    assert "apachectl configtest" in restore
    assert "apachectl graceful" in restore


def test_dependency_restore_checks_installed_environment() -> None:
    assert '"${ROOT}/.venv/bin/python" -m pip check' in SOURCE


def test_restart_failure_is_not_hidden_by_a_healthy_old_process() -> None:
    restart = SOURCE.split("restart_and_check() {", 1)[1].split("abort_update() {", 1)[0]
    assert 'systemctl restart "$SERVICE" || return 1' in restart


def test_first_transition_preserves_legacy_dispatcher_until_success() -> None:
    installer = SOURCE.split("install_launcher_link() {", 1)[1].split("rollback_transaction() {", 1)[0]
    update = SOURCE.split("do_update() {", 1)[1].split("do_rollback() {", 1)[0]
    assert '[[ "$0" == "/usr/local/sbin/bp-bootstrap" ]]' in installer
    assert 'mv -Tf "$temporary" "$launcher"' in installer
    assert update.index("restart_and_check") < update.index("install_launcher_link")
