FROM python:3.13.11-slim


COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
WORKDIR /code
COPY pipeline.py .
ENTRYPOINT ["python", "pipeline.py"]
