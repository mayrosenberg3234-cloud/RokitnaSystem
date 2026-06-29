#!/bin/bash
# Rokitna Project Management System — Mac/Linux launcher.
# Usage:  ./start.sh   (run from inside the project folder)
set -e
cd "$(dirname "$0")"

# Pick a Python 3 interpreter.
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "[שגיאה] לא נמצא Python. התקינו Python 3.10+ מ- https://www.python.org/downloads/"
  exit 1
fi

# Install requirements only on the first run.
if ! "$PY" -c "import streamlit" >/dev/null 2>&1; then
  echo "מתקין רכיבים נדרשים (פעם אחת, אנא המתינו)..."
  "$PY" -m pip install -r requirements.txt
fi

echo "מפעיל את המערכת... הדפדפן ייפתח אוטומטית. לעצירה: Ctrl+C"
exec "$PY" -m streamlit run app.py
