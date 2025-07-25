@echo off
echo Installing RupaGanti Bot dependencies...
echo.
echo Installing Python packages...
pip install --upgrade pip
pip install pyTelegramBotAPI==4.14.0
pip install Pillow==10.1.0
pip install cryptography==41.0.7
pip install PyMuPDF==1.23.8
pip install python-docx==1.1.0
pip install pdf2docx==0.5.6
pip install docx2pdf==0.1.8
pip install reportlab==4.0.7
pip install pandas==2.1.4
pip install openpyxl==3.1.2
pip install python-pptx==0.6.23
echo.
echo Dependencies installed successfully!
echo.
echo IMPORTANT: For video/audio conversion, you need FFmpeg:
echo 1. Download FFmpeg from https://ffmpeg.org/download.html
echo 2. Add FFmpeg to your system PATH
echo 3. Restart command prompt
echo.
echo Next steps:
echo 1. Make sure your bot token is correct in rupaganti_bot.py
echo 2. Run: python rupaganti_bot.py
echo.
pause