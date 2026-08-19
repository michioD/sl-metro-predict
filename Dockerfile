# Use a strict, slim Python base image to prevent container bloat
FROM python:3.9-slim

# Set environment variables to prevent python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' mlops-user

# Set the working directory
WORKDIR /app

# Install system dependencies if required (e.g., for compiling C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY src/ /app/src/
COPY models/ /app/models/

# Ensure the non-root user owns the app directory
RUN chown -R mlops-user:mlops-user /app
USER mlops-user

# Expose the FastAPI port
EXPOSE 8000

# Run the application via uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
