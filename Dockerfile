FROM ubuntu:20.04 as base
FROM base AS python3

ENV FLASK_CONFIG dev

RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    python3-dev \
    python3-pip \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

RUN set -ex \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 10

COPY requirements/base.txt /src/requirements/base.txt

RUN pip3 install -r /src/requirements/base.txt

COPY ./ /src

WORKDIR /src

CMD ["python", "run.py"]
