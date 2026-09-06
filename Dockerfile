FROM python:3.12-slim

# tzdata: slim images ship no zoneinfo database, needed for Europe/Berlin.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 bot
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY restaurant_bot ./restaurant_bot
COPY main.py .

RUN mkdir -p /app/data && chown -R bot:bot /app
USER bot

ENV SQLITE_PATH=/app/data/restaurants.db
CMD ["python", "main.py"]
