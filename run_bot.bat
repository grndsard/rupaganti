@echo off
echo 🚀 Starting RupaGanti Bot...
echo.
echo Checking dependencies...
python -c "import PIL; print('✅ Pillow OK')" 2>nul || echo "❌ Pillow missing - run setup.bat first"
python -c "import telebot; print('✅ TeleBot OK')" 2>nul || echo "❌ TeleBot missing - run setup.bat first"
echo.
echo Starting bot...
python rupaganti_bot.py
echo.
echo Bot stopped.
pause