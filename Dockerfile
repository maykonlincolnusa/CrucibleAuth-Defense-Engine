FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY scripts /app/scripts
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

RUN pip install --upgrade pip && pip install -e .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
