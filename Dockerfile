FROM python:3.12-slim
COPY --from=caddy:2 /usr/bin/caddy /usr/bin/caddy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=10000
EXPOSE 10000
CMD ["sh", "/app/deploy/start.sh"]
