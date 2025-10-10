FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY etl ./etl
COPY tests ./tests
COPY README.md ./README.md

CMD ["python", "-m", "etl.pipeline", "940GZZLUEBY", "--line-modes", "tube", "--line-service-types", "Regular"]

