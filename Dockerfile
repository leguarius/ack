FROM python:3.13-slim-trixie

# Bibliothèques système requises par WeasyPrint (TEC-067)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.lock pyproject.toml README.md ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

RUN useradd --system --uid 10001 --no-create-home ackdoc
USER ackdoc
ENV HOME=/tmp XDG_CACHE_HOME=/tmp PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
ENTRYPOINT ["ack-doc"]
