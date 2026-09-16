@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   ==========================================
echo      Look4End 发布
echo   ==========================================
echo.

git add -A

git diff --cached --quiet
if %errorlevel%==0 (
    echo   没有检测到任何改动，不需要发布。
    echo.
    pause
    exit /b
)

git commit -m "update %date% %time%"
if errorlevel 1 (
    echo.
    echo   [失败] 存档这一步出错了，把上面的报错发给 AI。
    echo.
    pause
    exit /b 1
)

echo.
git push
if errorlevel 1 (
    echo.
    echo   [失败] 上传这一步出错了，把上面的报错发给 AI。
    echo.
    pause
    exit /b 1
)

echo.
echo   ==========================================
echo      发布成功
echo      等 30 秒左右刷新 look4end.com
echo   ==========================================
echo.
pause
