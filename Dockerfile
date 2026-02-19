# Base Image
FROM python:3.10-slim

# Install system dependencies (Git as requested)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Dashboard Port
EXPOSE 8000

# Default Command: Start the Dashboard
CMD ["python", "run_dashboard_foreground.py"]
