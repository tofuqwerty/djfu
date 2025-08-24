# Gunakan image Python 3.12-slim sebagai base image
FROM python:3.12-slim

# Install ffmpeg dan dependensi sistem
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Salin requirements.txt dan install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file proyek ke container
COPY . .

# Jalankan bot
CMD ["python", "bot.py"]
