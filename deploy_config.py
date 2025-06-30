# PythonAnywhere deployment configuration
import os

# Use environment variable for bot token in production
BOT_TOKEN = os.getenv('BOT_TOKEN', '7650951465:AAF45TzccOAlDoSEqsOBd4lcHsxPGhMZEtE')

# Reduced cleanup time for free hosting
CLEANUP_INTERVAL_MINUTES = 10  # Instead of 60 minutes

# Smaller file size limits for free hosting
MAX_FILE_SIZE_MB = 10

print("Deployment config loaded for PythonAnywhere")