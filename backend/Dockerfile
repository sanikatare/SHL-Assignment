FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make sure there is always a catalog to serve, even on a cold deploy where
# the real scraper hasn't been run against the live SHL site yet.
RUN if [ ! -f catalog.json ] && [ -f sample_catalog.json ]; then cp sample_catalog.json catalog.json; fi

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
