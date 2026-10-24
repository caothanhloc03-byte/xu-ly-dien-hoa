@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist dist\DienHoaOrigin\DienHoaOrigin.exe ( echo Hay chay build.bat truoc. & pause & exit /b 1 )
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% ( echo Chua cai Inno Setup 6 - tai tai https://jrsoftware.org/isdl.php & pause & exit /b 1 )
%ISCC% installer.iss || ( echo *** CO LOI *** & pause & exit /b 1 )
echo XONG: setup\EchemStudio_Setup.exe
pause
