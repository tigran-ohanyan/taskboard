FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY static ./static
RUN pip install --no-cache-dir .

ENV DATABASE_URL=sqlite:////app/data/taskboard.db
VOLUME ["/app/data"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
