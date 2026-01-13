# ----------------------------------------------------------------------------- 
# base - Defines all settings common to all the stages 
# ----------------------------------------------------------------------------- 
FROM python:3.12-slim

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Timezone
RUN ln -snf /usr/share/zoneinfo/Asia/Bangkok /etc/localtime \
    && echo Asia/Bangkok > /etc/timezone

# Install system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    curl \
    unixodbc \
    unixodbc-dev \
    libgssapi-krb5-2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC
RUN curl -sSL https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -o packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --upgrade pip && pip install uv

# Copy dependency files first (for cache)
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen || true

# Copy source code
COPY . .

# Run app
ENTRYPOINT ["uv", "run", "python", "app.py"]

