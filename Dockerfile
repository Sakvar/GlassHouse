FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --gid 10001 glasshouse && useradd --uid 10001 --gid glasshouse --no-create-home glasshouse
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .
COPY apps ./apps
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
USER glasshouse
EXPOSE 8000
CMD ["python", "scripts/start_api.py"]
