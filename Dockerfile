FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (none for this bot)
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port Render expects
EXPOSE 10000

# Run the bot with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
