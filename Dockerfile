FROM python:3.10-slim

# Install build tools required for some Python packages (e.g. Firestore) on slim image
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data during build to avoid runtime SSL issues
RUN python -m nltk.downloader punkt stopwords vader_lexicon

COPY . .

ENV PORT=8080

CMD ["python", "startup.py"] 