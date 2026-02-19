@echo off
echo Остановка всех процессов Python...
taskkill /F /IM python.exe /T 2>nul
if %errorlevel% == 0 (
    echo Все процессы Python остановлены
) else (
    echo Процессы Python не найдены или уже остановлены
)
pause
