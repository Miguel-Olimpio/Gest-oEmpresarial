@echo off
setlocal
cd /d "%~dp0"

echo Instalando dependencias...
python -m pip install -r requirements.txt

echo.
echo Limpando build anterior...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Gerando executavel...
pyinstaller --clean --noconfirm GestaoEmpresarial.spec

if not exist "dist\GestaoEmpresarial\data" mkdir "dist\GestaoEmpresarial\data"
if not exist "dist\GestaoEmpresarial\pdfs" mkdir "dist\GestaoEmpresarial\pdfs"
if not exist "dist\GestaoEmpresarial\backups" mkdir "dist\GestaoEmpresarial\backups"
if not exist "dist\GestaoEmpresarial\icon" mkdir "dist\GestaoEmpresarial\icon"

if exist "icon\icon.ico" copy /Y "icon\icon.ico" "dist\GestaoEmpresarial\icon\icon.ico" >nul

echo.
echo Finalizado.
echo O executavel fica em dist\GestaoEmpresarial\GestaoEmpresarial.exe.
echo O icone usado no executavel e na janela e icon\icon.ico.
endlocal
pause
