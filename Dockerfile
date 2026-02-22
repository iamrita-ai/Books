FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (none required for this fix)
# Upgrade pip and install setuptools first to ensure availability
RUN pip install --no-cache-dir --upgrade pip setuptools==65.6.3 wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
