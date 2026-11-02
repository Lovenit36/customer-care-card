FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=3000 HOST=0.0.0.0 DATA_DIR=/app/storage
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py care_logic.py pdf_tools.py retrieval.py schedule_logic.py ./
COPY static ./static
RUN mkdir -p /app/storage && useradd --system --uid 10001 care && chown -R care:care /app
USER care
EXPOSE 3000
CMD ["python","server.py"]
