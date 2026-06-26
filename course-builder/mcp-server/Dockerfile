# Autonomous Course-Builder — MCP tool server (the "decoupling" seam).
#
#   docker build -t course-builder-mcp .   # run from course-builder/mcp-server/
#
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Local tool backends + the seeded course materials/catalog.
COPY lib/ ./lib/
COPY seed/ ./seed/
COPY mcp_tools.py server.py ./

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "echo '(c) Dr. Tim Smith, 2026' && python server.py"]
