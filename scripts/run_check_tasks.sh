#!/bin/bash

# Loyiha papkasiga kirish
cd /app_and_apps/dms_app/DMS_API/

# Virtual muhitni ishga tushirish (ixtiyoriy, lekin foydali)
source flow_venv/bin/activate

# Django buyrug'ini ishga tushirish
python manage.py check_tasks

# Tamom
deactivate