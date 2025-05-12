# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

COPY uv.lock .
COPY pyproject.toml .

# Install the project's dependencies using the lockfile and settings
RUN uv sync --frozen --no-install-project --no-dev --no-editable

COPY . .
RUN uv sync --frozen --no-dev --no-editable

RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg curl apt-transport-https && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev && \
    rm -rf /var/lib/apt/lists/*

CMD ["uv", "run", "/app/main.py"]