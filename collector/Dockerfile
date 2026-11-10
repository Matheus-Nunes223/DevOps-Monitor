FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY config.yaml ./
COPY src ./src
RUN uv sync --no-dev
USER 10001:10001
ENTRYPOINT ["devops-monitor"]
