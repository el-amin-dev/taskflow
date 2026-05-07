FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

COPY requirements.lock ./
RUN pip install --prefix=/install -r requirements.lock


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:${PATH}"

RUN groupadd --system --gid 1001 app \
&& useradd  --system --uid 1001 --gid app --no-create-home app

WORKDIR /app

COPY --from=builder /install /usr/local 
COPY --chown=app:app app ./app

USER app

EXPOSE 8000


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]