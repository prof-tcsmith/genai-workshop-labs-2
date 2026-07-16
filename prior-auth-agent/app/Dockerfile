# Prior-Auth Triage — the agentic app (orchestrator + agents + UI).
#
#   docker build -t prior-auth-app .   # run from prior-auth-agent/app/
#
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lib/ ./lib/
COPY streamlit_app.py .

EXPOSE 8501

CMD ["sh", "-c", "echo '(c) Dr. Tim Smith, 2026' && streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false"]
