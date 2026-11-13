#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="blind-ham-propagation"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_FILE="/etc/blind-ham-propagation.env"
SERVICE_USER="blindham-prop"
SERVICE_GROUP="blindham-prop"
PORT="${BLIND_HAM_PROPAGATION_PORT:-8765}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Запусти скрипт от root: bash scripts/install_vds.sh" >&2
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo "Не найден git. Установи его через apt." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "Не найден python3. Установи Python 3." >&2
    exit 1
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
        echo "==> Установка системного пакета python3-venv"
        apt-get update
        apt-get install -y python3-venv python3-pip
    else
        echo "Не найден модуль venv. Установи пакет python3-venv." >&2
        exit 1
    fi
fi

if systemctl cat "${SERVICE_NAME}.service" >/dev/null 2>&1; then
    echo "Служба ${SERVICE_NAME} уже установлена." >&2
    echo "Этот скрипт предназначен только для первоначальной установки." >&2
    echo "Обновление существующей установки этим установщиком не выполняется." >&2
    echo "Для обновления существующей установки используй команду bp update." >&2
    echo "Сначала установи scripts/bp в /usr/local/sbin/bp, если команда ещё не установлена." >&2
    exit 1
fi

if [[ ! -d "${ROOT}/.git" ]]; then
    echo "Каталог ${ROOT} не является Git checkout." >&2
    echo "Сначала клонируй репозиторий на нужный коммит." >&2
    exit 1
fi

echo "==> Первоначальная установка из checkout: ${ROOT}"

if ! getent group "${SERVICE_GROUP}" >/dev/null 2>&1; then
    groupadd --system "${SERVICE_GROUP}"
fi
if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd --system --gid "${SERVICE_GROUP}" --home-dir "${ROOT}" --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

if ! runuser -u "${SERVICE_USER}" -- test -x "${ROOT}"; then
    echo "Пользователь службы не может пройти к каталогу проекта: ${ROOT}" >&2
    echo "Размести репозиторий, например, в /var/www/ или /opt/, а не в закрытом /root." >&2
    exit 1
fi

if [[ ! -x "${ROOT}/.venv/bin/python" ]]; then
    echo "==> Создание виртуального окружения"
    python3 -m venv "${ROOT}/.venv"
fi
if ! "${ROOT}/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
    "${ROOT}/.venv/bin/python" -m ensurepip --upgrade
fi

if [[ ! -f "${ROOT}/requirements-vds.lock" ]]; then
    echo "Не найден requirements-vds.lock. Отказ от установки без зафиксированных зависимостей." >&2
    exit 1
fi

echo "==> Установка зафиксированных Python-зависимостей"
"${ROOT}/.venv/bin/python" -m pip install -r "${ROOT}/requirements-vds.lock"

echo "==> Установка приложения из текущего checkout"
"${ROOT}/.venv/bin/python" -m pip install --no-deps --no-build-isolation "${ROOT}"

install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${ROOT}/data" "${ROOT}/logs"
if [[ ! -f "${ROOT}/settings.ini" ]]; then
    cat > "${ROOT}/settings.ini" <<'INI'
[psk_reporter]
enabled = true
topics = pskr/filter/v2/20m/FT8/#

[yandex_maps]
javascript_api_key =
INI
    chown root:"${SERVICE_GROUP}" "${ROOT}/settings.ini"
    chmod 0640 "${ROOT}/settings.ini"
fi

cat > "${SERVICE_FILE}" <<UNIT
[Unit]
Description=Blind-Ham Propagation web service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${ROOT}
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=${ROOT}/.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port ${PORT} --proxy-headers
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=${ROOT}/data ${ROOT}/logs

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

echo
echo "==> Состояние службы:"
systemctl --no-pager --full status "${SERVICE_NAME}.service" || true
echo
echo "Служба установлена: ${SERVICE_NAME}.service"
echo "Локальный backend слушает 127.0.0.1:${PORT}."
echo "Настройки сборщика: ${ROOT}/settings.ini"
echo "Логи: journalctl -u ${SERVICE_NAME}.service -f"
