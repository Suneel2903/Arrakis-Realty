# Cloud Run Job image for the K-RERA pipeline.
FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.8.17
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev
RUN useradd --create-home --uid 10001 pipeline
USER pipeline
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["python", "-m", "rera_pipeline"]
CMD ["--help"]
