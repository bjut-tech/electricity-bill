FROM debian:12-slim AS build

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes git python3-venv gcc libpython3-dev && \
    python3 -m venv /venv && \
    /venv/bin/pip install --upgrade pip setuptools wheel

FROM build AS build-venv

WORKDIR /app

COPY requirements.txt ./

RUN /venv/bin/pip install --disable-pip-version-check --no-cache-dir --upgrade -r requirements.txt

FROM gcr.io/distroless/python3-debian12

WORKDIR /app

COPY --from=build-venv /venv /venv
COPY main.py ./

ENTRYPOINT ["/venv/bin/python3", "main.py"]
