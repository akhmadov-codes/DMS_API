@echo off
REM 1. Eski distni butunlay o'chirish
if exist dist rmdir /s /q dist

REM 2. Faqat kerakli narsalarni shifrlash (venv'siz)
echo Shifrlash boshlandi...
pyarmor gen --platform linux.x86_64 -r manage.py config flow_document flow_task flow_taskres flow_user

REM 3. Agar dist ichiga tasodifan flow_venv kirib qolgan bo'lsa, uni o'chirish
if exist dist\flow_venv rmdir /s /q dist\flow_venv

REM 4. Kerakli qo'shimcha fayllarni nusxalash
copy requirements.txt dist\
REM Serverdagi .env alohida saqlanadi (DEBUG=False, SECRET_KEY, DB_*); lokal .env nusxalanmaydi
copy .env.example dist\

echo Build muvaffaqiyatli yakunlandi!
pause
