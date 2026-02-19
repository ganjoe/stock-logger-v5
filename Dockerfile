# Base Image
FROM python:3.11-slim

# Install system dependencies (Git as requested)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Step 1: Copy requirements FIRST for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 2: Copy the rest of the code
COPY . .

# Expose Dashboard Port
EXPOSE 8000

# Start script (Note: main_cli.py for CLI or run_dashboard_foreground.py for Web)
CMD ["python", "main_cli.py"]
