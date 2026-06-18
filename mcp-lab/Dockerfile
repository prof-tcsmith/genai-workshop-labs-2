FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Serve over HTTP so the container is reachable (Cloud Run injects $PORT).
ENV MCP_TRANSPORT=streamable-http
ENV PORT=8000
EXPOSE 8000

CMD ["python", "server.py"]
