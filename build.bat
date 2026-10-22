@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai thu vien ===
python -m pip install --upgrade pyinstaller originpro numpy pandas matplotlib || goto loi
echo === Dong goi (chi chua Python + thu vien, ma nguon de ben ngoai) ===
python -m PyInstaller --noconfirm --clean --onedir --name DienHoaOrigin --icon logo.ico ^
  --collect-all originpro --collect-all OriginExt ^
  --hidden-import win32com.client --hidden-import pythoncom ^
  launcher.py || goto loi
echo === Chep ma nguon vao dist\DienHoaOrigin\ma_nguon ===
set OUT=dist\DienHoaOrigin\ma_nguon
mkdir "%OUT%" 2>nul
for %%F in (giao_dien.pyw ve_origin.py xu_ly_dien_hoa.py tu_dong_cap_nhat.py version.json logo.ico) do copy /Y "%%F" "%OUT%\" >nul
echo.
echo === XONG ===
echo Nen thu muc  %~dp0dist\DienHoaOrigin  thanh .zip de gui dong nghiep.
pause
exit /b 0
:loi
echo.
echo *** CO LOI - xem thong bao phia tren ***
pause
exit /b 1
