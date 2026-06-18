FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=8501
EXPOSE 8501

CMD ["sh", "-c", "echo '============================================'; echo '  GenAI Workshop — live demos'; echo '  (c) Dr. Tim Smith, 2026'; echo '============================================'; streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true"]
