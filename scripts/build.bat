@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  GrayScope — Windows Installer Builder
echo ========================================
echo.

:: Locate Python
where python >nul 2>&1 || (echo [ERROR] python bulunamadi. PATH kontrol edin. & exit /b 1)

:: Step 1 – Generate icon
echo [1/3] Ikon olusturuluyor...
python scripts\generate_icon.py || exit /b 1
echo.

:: Step 2 – PyInstaller
echo [2/3] PyInstaller ile paketleniyor...
python -m PyInstaller grayscope.spec --noconfirm --clean || exit /b 1
echo.

:: Step 3 – Inno Setup (optional, only if ISCC is on PATH or in default location)
set ISCC=
for %%p in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) do (
    if exist %%p set ISCC=%%~p
)

echo [3/3] Inno Setup kurulum paketi olusturuluyor...
if "!ISCC!"=="" (
    echo [UYARI] Inno Setup bulunamadi.
    echo         Kurmak icin: https://jrsoftware.org/isdl.php
    echo         Kurulduktan sonra bu scripti tekrar calistirin.
    echo         ya da: ISCC.exe installer\grayscope.iss
) else (
    mkdir installer\output 2>nul
    "!ISCC!" installer\grayscope.iss || exit /b 1
    echo.
    echo [OK] Kurulum paketi: installer\output\GrayScope-0.1.0-Setup.exe
)

echo.
echo Tamamlandi!
echo   Calistirmak icin: dist\GrayScope\GrayScope.exe
endlocal
