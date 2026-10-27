FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PORT=8501

COPY requirements-app.txt ./
RUN pip install --no-cache-dir -r requirements-app.txt

COPY .streamlit ./.streamlit
COPY app.py ./
COPY src ./src
COPY models/advanced_model_bundle.joblib models/similarity_index.joblib models/history_models.joblib ./models/
COPY knowledge ./knowledge

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/_stcore/health' % os.environ.get('PORT','8501'))"

CMD ["sh", "-c", "streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT}"]
