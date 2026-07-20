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
    && python3 -m py_compile \
        scripts/check-showdown-user.py \
        scripts/prepare-foul-play-cache.py \
        scripts/patch-foul-play-local-login.py \
        scripts/test-foul-play-local-login.py \
    && bash -n scripts/showdown-ai.sh \
    && bash -n scripts/render-start.sh \
    && bash -n scripts/sync-bss-teams.sh \
    && bash -n scripts/sync-all-generations-teams.sh

# Render does not guarantee that Git submodules are initialized for a Docker
# build, so fetch foul-play explicitly and pin the revision already used by this
# repository. The private loopback server accepts passwordless /trn logins, so
# bypass the public assertion service for this one trusted local connection.
RUN rm -rf foul-play \
    && git clone --filter=blob:none https://github.com/pmariglia/foul-play.git foul-play \
    && git -C foul-play checkout 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6 \
    && python3 scripts/patch-foul-play-local-login.py

RUN node build \
    && python3 -m venv .venv \
    && .venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && .venv/bin/python -m pip install --no-cache-dir -r foul-play/requirements.txt \
    && .venv/bin/python scripts/test-foul-play-local-login.py

# Validate one embedded team first so format or set errors are explicit in build
# logs instead of being hidden by the bulk library importer.
RUN bash scripts/ensure-codespaces-config.sh \
    && node pokemon-showdown validate-team gen9nationaldexallgenerationsbss --skip-build \
        < config/all-generations-fallback/01-legendary-offense.txt

# The embedded teams guarantee an offline fallback. Public National Dex teams
# are added when the community API is reachable during the image build. Usage
# statistics are cached too, avoiding a large download on the first battle after
# every free-service wake-up.
RUN bash scripts/sync-all-generations-teams.sh --refresh \
    && python3 scripts/prepare-foul-play-cache.py

EXPOSE 10000

CMD ["bash", "scripts/render-start.sh"]
