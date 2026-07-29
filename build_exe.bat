@echo off
title Build HotspotDashboard EXE
cd /D "%~dp0"

echo ================================================
echo   热点聚合工作台 - EXE 打包工具
echo ================================================
echo.

:: 1. 重新构建前端
echo [1/3] 构建前端...
cd frontend
call npm run build
if errorlevel 1 goto :error
cd ..
echo     OK 前端构建完成
echo.

:: 2. 用 PyInstaller 打包
echo [2/3] 打包 EXE（首次较慢，约 1-2 分钟）...
"C:\Users\blbnb\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m PyInstaller ^
    --clean ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --add-data "backend;backend" ^
    --add-data "frontend/dist;frontend/dist" ^
    --name "HotspotDashboard" ^
    bundle_entry.py
if errorlevel 1 goto :error
echo     OK EXE 打包完成
echo.

echo ================================================
echo   打包成功！
echo   EXE 文件位置: %~dp0dist\HotspotDashboard.exe
echo ================================================
echo.
pause
exit /b 0

:error
echo.
echo [错误] 打包失败，请检查上面的输出
pause
exit /b 1