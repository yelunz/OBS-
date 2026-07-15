@echo off
chcp 65001 >nul
REM ============================================================
REM OBS多视角切换器 - 打包构建脚本
REM 用法: 双击运行或在命令行执行 build.bat
REM 依赖: PyInstaller (pip install pyinstaller)
REM ============================================================

echo ============================================
echo   OBS多视角切换器 - 打包构建
echo ============================================
echo.

REM 步骤1: PyInstaller 打包
echo [1/2] 正在执行 PyInstaller 打包...
py -m PyInstaller --noconfirm --clean --windowed ^
  --name "OBS多视角切换器" ^
  --icon "app_icon.ico" ^
  --add-data "app_icon.ico;." ^
  --add-data "templates;templates" ^
  --add-data "mediamtx.exe;." ^
  --add-data "mediamtx.yml;." ^
  --add-data "config.json;." ^
  --hidden-import "vlc" ^
  --hidden-import "PIL" ^
  --hidden-import "PIL.Image" ^
  --hidden-import "PIL.ImageTk" ^
  --hidden-import "pynput.mouse" ^
  --hidden-import "pynput.keyboard" ^
  --collect-all simple_websocket ^
  --collect-all engineio ^
  --collect-all flask_socketio ^
  --distpath "dist" ^
  --workpath "build" ^
  "OBS多视角切换器.pyw"

if errorlevel 1 (
    echo.
    echo [错误] PyInstaller 打包失败!
    pause
    exit /b 1
)
echo.
echo [成功] PyInstaller 打包完成 -^ dist\OBS多视角切换器\
echo.

REM 步骤2: Inno Setup 编译安装包
echo [2/2] 正在编译 Inno Setup 安装包...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer.iss"

if errorlevel 1 (
    echo.
    echo [错误] Inno Setup 编译失败!
    pause
    exit /b 1
)
echo.
echo ============================================
echo   全部完成!
echo   安装包: installer_output\OBS多视角切换器_安装包_v1.0.0.exe
echo ============================================
pause
