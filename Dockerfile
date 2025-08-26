FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for API
EXPOSE 8000

# Command for tts-api (overridden in docker-compose.yml for gradio-ui)
CMD ["python", "-m", "uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]