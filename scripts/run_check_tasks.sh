#!/bin/bash
# Muddati o'tgan topshiriqlarni tekshirish (cron orqali ishga tushiriladi).
# Natija logs/check_tasks.log fayliga yoziladi.
set -euo pipefail

PROJECT_DIR="/dms/www/DMS_API"

cd "$PROJECT_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] check_tasks boshlandi" >> logs/check_tasks.log
./flow_venv/bin/python manage.py check_tasks >> logs/check_tasks.log 2>&1
