#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="blind-ham-propagation"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
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

echo "==> Обновление репозитория: ${ROOT}"
git -C "${ROOT}" pull --ff-only

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd --system --home-dir "${ROOT}" --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

if [[ ! -x "${ROOT}/.venv/bin/python" ]]; then
    echo "==> Создание виртуального окружения"
    python3 -m venv "${ROOT}/.venv"
fi

echo "==> Обновление Python-зависимостей"
"${ROOT}/.venv/bin/python" -m pip install --upgrade pip
"${ROOT}/.venv/bin/python" -m pip install --upgrade -r "${ROOT}/requirements.txt"

install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${ROOT}/data" "${ROOT}/logs"

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
ProtectHome=true
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
echo "Логи: journalctl -u ${SERVICE_NAME}.service -f"
