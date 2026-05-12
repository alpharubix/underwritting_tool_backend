
# Use official lightweight Python image
FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered logs (important for Cloud Run)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run injects PORT env var — default to 8080
ENV PORT=8080

# Start the app using uvicorn directly
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]