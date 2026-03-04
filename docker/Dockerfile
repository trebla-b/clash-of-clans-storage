FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache tzdata

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV APP_CONFIG=/app/config/config.yml

ENTRYPOINT ["/entrypoint.sh"]
