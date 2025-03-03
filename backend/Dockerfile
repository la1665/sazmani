FROM python:3.11-slim

# Environment variables to improve container behavior
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install necessary system dependencies, including OpenGL libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    postgresql-client \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set the working directory
WORKDIR /app

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create necessary directories with appropriate permissions
# RUN mkdir -p logs && chmod 755 logs
# RUN mkdir -p uploads && chmod 755 uploads
# Ensure /app/uploads has the correct permissions inside the backend container
RUN mkdir -p /app/logs && chmod -R 755 /app/logs
RUN mkdir -p /app/uploads && chmod -R 755 /app/uploads

# Expose the application port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "main:app_socket", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "debug"]
