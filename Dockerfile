FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.cargo/bin:/app/.venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        pkg-config \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --profile minimal

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN node --check scripts/launcher-server.js \
    && bash -n scripts/showdown-ai.sh \
    && bash -n scripts/render-start.sh \
    && bash -n scripts/sync-bss-teams.sh \
    && bash -n scripts/sync-all-generations-teams.sh

# Render does not guarantee that Git submodules are initialized for a Docker
# build, so fetch foul-play explicitly and pin the revision already used by this
# repository.
RUN rm -rf foul-play \
    && git clone --filter=blob:none https://github.com/pmariglia/foul-play.git foul-play \
    && git -C foul-play checkout 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6

RUN node build \
    && python3 -m venv .venv \
    && .venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && .venv/bin/python -m pip install --no-cache-dir -r foul-play/requirements.txt

# The embedded teams guarantee an offline fallback. Public National Dex teams
# are added when the community API is reachable during the image build.
RUN bash scripts/ensure-codespaces-config.sh \
    && bash scripts/sync-all-generations-teams.sh --refresh

EXPOSE 10000

CMD ["bash", "scripts/render-start.sh"]
