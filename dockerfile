# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first
COPY requirements.txt .

# Install Python dependencies with increased timeout
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt

# Install google-adk separately without dependency checks to avoid conflicts
RUN pip install --no-cache-dir --no-deps google-adk==0.2.0

# Copy the entire application
COPY . .

# Create necessary directories
RUN mkdir -p chroma_db logs .credentials

# Create a simple startup script
COPY <<EOF /app/start.sh
#!/bin/sh

# Create Firebase service account JSON from environment variables
if [ ! -z "\$FIREBASE_PROJECT_ID" ]; then
  echo "Creating Firebase credentials from environment variables..."
  
  # Create JSON file with properly escaped private key
  cat > /app/.credentials/service-account.json << "FIREBASE_JSON"
{
  "type": "\$FIREBASE_TYPE",
  "project_id": "\$FIREBASE_PROJECT_ID",
  "private_key_id": "\$FIREBASE_PRIVATE_KEY_ID",
  "private_key": "PRIVATE_KEY_PLACEHOLDER",
  "client_email": "\$FIREBASE_CLIENT_EMAIL",
  "client_id": "\$FIREBASE_CLIENT_ID",
  "auth_uri": "\$FIREBASE_AUTH_URI",
  "token_uri": "\$FIREBASE_TOKEN_URI",
  "auth_provider_x509_cert_url": "\$FIREBASE_AUTH_PROVIDER_X509_CERT_URL",
  "client_x509_cert_url": "\$FIREBASE_CLIENT_X509_CERT_URL",
  "universe_domain": "\$FIREBASE_UNIVERSE_DOMAIN"
}
FIREBASE_JSON

  # Replace the private key placeholder with the actual private key (properly escaped)
  # This handles the newlines correctly by keeping them as \n in the JSON
  sed -i "s|PRIVATE_KEY_PLACEHOLDER|\$FIREBASE_PRIVATE_KEY|g" /app/.credentials/service-account.json
  
  echo "✅ Firebase credentials created"
else
  echo "⚠️ No Firebase environment variables found"
fi

# Start the application
exec python main.py
EOF

# Make startup script executable
RUN chmod +x /app/start.sh

# Expose the port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application via startup script
CMD ["/app/start.sh"]