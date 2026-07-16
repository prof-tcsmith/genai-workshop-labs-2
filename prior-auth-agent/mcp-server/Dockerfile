# Prior-Auth Triage — MCP tool server (the "decoupling" seam).
#
#   docker build -t prior-auth-mcp .   # run from prior-auth-agent/mcp-server/
#
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Local tool backends + the seeded coverage policies.
COPY lib/ ./lib/
COPY seed/ ./seed/
COPY mcp_tools.py server.py ./

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "echo '(c) Dr. Tim Smith, 2026' && python server.py"]
