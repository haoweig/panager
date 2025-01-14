# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for cryptography
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p certs
RUN mkdir -p users
RUN mkdir -p password
RUN mkdir -p key

# Copy only specific files
COPY main.py .
COPY password_manager.py .
COPY certs/cert.pem certs/
COPY certs/key.pem certs/

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]