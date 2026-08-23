#!/usr/bin/env bash
set -euo pipefail

APP_NAME="telegraph-writer"
REPO_URL="https://github.com/seguidodoblado/telegraph-writer.git"
INSTALL_DIR="/opt/telegraph-writer"
VENV_DIR="$HOME/.venvs/telegraph-writer"
ICON_DIR="$HOME/.local/share/icons"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APP_DIR/telegraph-writer.desktop"

info() {
    printf '\033[1;34m==>\033[0m %s\n' "$1"
}

fail() {
    printf '\033[1;31mError:\033[0m %s\n' "$1" >&2
    exit 1
}

if [[ "${EUID}" -eq 0 ]]; then
    fail "No ejecutes este instalador como root. Ejecútalo con tu usuario normal; el script usará sudo cuando sea necesario."
fi

command -v git >/dev/null 2>&1 || fail "Git no está instalado. Instálalo con: sudo apt install git"
command -v python3 >/dev/null 2>&1 || fail "Python 3 no está instalado. Instálalo con: sudo apt install python3 python3-venv"
command -v sudo >/dev/null 2>&1 || fail "sudo no está disponible."

if ! python3 -m venv --help >/dev/null 2>&1; then
    fail "El módulo venv no está disponible. Instálalo con: sudo apt install python3-venv"
fi

info "Instalando Telegraph Writer en ${INSTALL_DIR}"

if [[ -d "${INSTALL_DIR}/.git" ]]; then
    info "La instalación ya existe; actualizando desde GitHub"
    sudo git -C "${INSTALL_DIR}" pull --ff-only
else
    if [[ -e "${INSTALL_DIR}" ]]; then
        fail "${INSTALL_DIR} ya existe pero no parece una instalación Git válida."
    fi

    sudo mkdir -p "$(dirname "${INSTALL_DIR}")"
    sudo git clone "${REPO_URL}" "${INSTALL_DIR}"
fi

info "Asignando la instalación al usuario ${USER}"
sudo chown -R "${USER}:${USER}" "${INSTALL_DIR}"

info "Creando entorno virtual en ${VENV_DIR}"
mkdir -p "$(dirname "${VENV_DIR}")"

if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
fi

info "Instalando dependencias"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

info "Instalando icono"
mkdir -p "${ICON_DIR}"
cp "${INSTALL_DIR}/telegraph-writer.svg" "${ICON_DIR}/telegraph-writer.svg"

info "Instalando lanzador de escritorio"
mkdir -p "${APP_DIR}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Telegraph Writer
Comment=Cliente de escritorio para Telegra.ph
Exec=${VENV_DIR}/bin/python ${INSTALL_DIR}/telegraph_writer_qt.py
Icon=${ICON_DIR}/telegraph-writer.svg
Terminal=false
Categories=Office;TextEditor;Utility;
StartupNotify=true
EOF

chmod +x "${DESKTOP_FILE}"

# Actualiza la caché de aplicaciones si la herramienta está disponible.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
fi

info "Instalación completada"
printf '\nTelegraph Writer está instalado en:\n  %s\n' "${INSTALL_DIR}"
printf 'Entorno Python:\n  %s\n' "${VENV_DIR}"
printf 'Lanzador:\n  %s\n\n' "${DESKTOP_FILE}"
printf 'Puedes buscar "Telegraph Writer" en el menú de aplicaciones de Linux Mint.\n'
printf 'Para actualizarlo en el futuro, vuelve a ejecutar este script o haz:\n'
printf '  cd %s && git pull\n' "${INSTALL_DIR}"
