FROM node:22-bookworm AS client-builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build-context

COPY config/pokemon-showdown-client.json config/pokemon-showdown-client.json
COPY scripts/check-built-client.py scripts/check-built-client.py

RUN set -eux; \
    CLIENT_REPOSITORY="$(node -e "process.stdout.write(require('/build-context/config/pokemon-showdown-client.json').fork_repository)")"; \
    CLIENT_SHA="$(node -e "process.stdout.write(require('/build-context/config/pokemon-showdown-client.json').commit)")"; \
    git init /client; \
    git -C /client remote add origin "https://github.com/${CLIENT_REPOSITORY}.git"; \
    git -C /client fetch --depth 1 origin "${CLIENT_SHA}:refs/remotes/origin/master"; \
    git -C /client checkout --detach "${CLIENT_SHA}"; \
    test "$(git -C /client rev-parse HEAD)" = "${CLIENT_SHA}"; \
    npm --prefix /client ci; \
    npm --prefix /client run build; \
    python3 scripts/check-built-client.py \
        --client-root /client \
        --pin-file config/pokemon-showdown-client.json \
        --write-manifest; \
    rm -rf /client/node_modules /client/.git

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

ENV PINNED_CLIENT_ROOT=/opt/pokemon-showdown-client

RUN npx eslint --max-warnings 0 \
        scripts/launcher-server.js \
        scripts/pinned-client-preload.js \
        scripts/test-launcher-japanese-language.js \
        scripts/test-launcher-pinned-client.js \
    && node --check scripts/launcher-server.js \
    && node --check scripts/pinned-client-preload.js \
    && node --check scripts/test-launcher-japanese-language.js \
    && node --check scripts/test-launcher-pinned-client.js \
    && node scripts/test-launcher-japanese-language.js \
    && node scripts/test-launcher-pinned-client.js \
    && python3 -m py_compile \
        scripts/check-built-client.py \
        scripts/check-localization-docs.py \
        scripts/check-pinned-client.py \
        scripts/check-showdown-user.py \
        scripts/prepare-foul-play-cache.py \
        scripts/patch-foul-play-local-login.py \
        scripts/patch-foul-play-battle-fallbacks.py \
        scripts/patch-foul-play-post-faint.py \
        scripts/smoke-bss-battle.py \
        scripts/smoke-bss-faint-recovery.py \
        scripts/test-foul-play-local-login.py \
        scripts/test-foul-play-battle-fallbacks.py \
    && python3 scripts/check-localization-docs.py \
    && bash -n scripts/showdown-ai.sh \
    && bash -n scripts/render-start.sh \
    && bash -n scripts/sync-bss-teams.sh \
    && bash -n scripts/sync-all-generations-teams.sh

# Render does not guarantee that Git submodules are initialized for a Docker
# build, so fetch foul-play explicitly and pin the revision already used by this
# repository. Apply private-server login and battle-safety patches afterwards.
RUN rm -rf foul-play \
    && git clone --filter=blob:none https://github.com/pmariglia/foul-play.git foul-play \
    && git -C foul-play checkout 25c976f05cbf2880eaa579afd6db1dcb2c3b57c6 \
    && python3 scripts/patch-foul-play-local-login.py \
    && python3 scripts/patch-foul-play-battle-fallbacks.py \
    && python3 scripts/patch-foul-play-post-faint.py

RUN node build \
    && python3 -m venv .venv \
    && .venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && .venv/bin/python -m pip install --no-cache-dir -r foul-play/requirements.txt \
    && .venv/bin/python scripts/test-foul-play-local-login.py \
    && .venv/bin/python scripts/test-foul-play-battle-fallbacks.py

# Validate the embedded bot team and both opponents used by the end-to-end BSS
# smoke tests.
RUN bash scripts/ensure-codespaces-config.sh \
    && node pokemon-showdown validate-team gen9nationaldexallgenerationsbss --skip-build \
        < config/all-generations-fallback/01-legendary-offense.txt \
    && node pokemon-showdown validate-team gen9nationaldexallgenerationsbss --skip-build \
        < config/bss-smoke-opponent.txt \
    && node pokemon-showdown validate-team gen9nationaldexallgenerationsbss --skip-build \
        < config/bss-faint-smoke-opponent.txt

# The embedded teams guarantee an offline fallback. Public National Dex teams
# are added when the community API is reachable during the image build. Usage
# statistics are cached too, avoiding a large download on the first battle after
# every free-service wake-up.
RUN bash scripts/sync-all-generations-teams.sh --refresh \
    && python3 scripts/prepare-foul-play-cache.py

# Keep the client outside /app so later server CLI invocations do not traverse
# client-only sources or symlinks while checking whether a server rebuild is due.
COPY --from=client-builder /client /opt/pokemon-showdown-client
RUN python3 scripts/check-built-client.py \
        --client-root /opt/pokemon-showdown-client \
        --pin-file /app/config/pokemon-showdown-client.json

EXPOSE 10000

CMD ["bash", "scripts/render-start.sh"]
