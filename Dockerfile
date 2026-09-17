FROM python:3.11-slim

# pyzbar needs the native zbar library; pip cannot supply it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libzbar0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so editing source does not invalidate this layer.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[web]"

COPY . .

EXPOSE 8501

# Default to the UI; `docker compose run` overrides this for CLI use.
CMD ["streamlit", "run", "web/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
