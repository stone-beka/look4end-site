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
if %errorlevel%==0 goto nothing_staged
goto do_commit

:do_commit
git commit -m "update %date% %time%"
if errorlevel 1 (
    echo.
    echo   [失败] 存档这一步出错了，把上面的报错发给 AI。
    echo.
    pause
    exit /b 1
)
goto do_push

:nothing_staged
rem No staged changes. But a commit may be sitting unpushed (a push that
rem failed on the network) -- push that too. Before this, double-clicking
rem did nothing at all in that state and looked like a success.
rem Keep this file ASCII outside the echo lines: Chinese in comments makes
rem cmd.exe split a line mid-character at some byte offsets (hit 2026-09-17).
git status -sb | findstr /C:"[ahead " >nul
if errorlevel 1 (
    echo   没有检测到任何改动，不需要发布。
    echo.
    pause
    exit /b
)
echo   没有新改动，但有攒着没推上去的，补推一次。

:do_push
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
echo     发布成功
echo     等 30 秒左右刷新 look4end.com
echo   ==========================================
echo.
pause
