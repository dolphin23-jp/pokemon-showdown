# Phase 1 T1-03: build the pinned client in Docker

T1-03 makes the fixed `pokemon-showdown-client` source reproducibly buildable inside the application image. It does not change which client is served to browser users.

## Build input

The Docker build reads `config/pokemon-showdown-client.json` and uses:

- repository: `dolphin23-jp/pokemon-showdown-client`
- commit: `085dfabd9bc53c730ac459edf5c28088677adfc2`

The builder initializes an empty Git repository, fetches only the exact full SHA, records that SHA as `origin/master` for the client build version, and checks out a detached HEAD. It does not build from a moving branch or tag.

## Build process

The dedicated `client-builder` Docker stage runs:

1. `npm ci`
2. `npm run build`
3. `scripts/check-built-client.py --write-manifest`
4. removal of `node_modules` and `.git`

The resulting source tree and generated artifacts are copied to:

- `/opt/pokemon-showdown-client`

The generated build manifest is:

- `/opt/pokemon-showdown-client/build-manifest.json`

The client is kept outside `/app`, which is the Pokémon Showdown server source tree. This prevents later server CLI commands such as team packing from traversing client-only files while checking whether a server rebuild is required.

The manifest records the fork, upstream, complete commit, client version, build command, file sizes, and SHA-256 hashes for representative local test-client HTML, generated JavaScript, CSS, and configuration files.

## Verification

The build verifier requires:

- the embedded client version to contain the pinned commit prefix
- the local `testclient-new.html` entry point
- references from that entry point to the compiled client CSS and JavaScript
- expected generated files such as `client-main.js`, `client-connection.js`, and `panel-battle.js`
- an exact match between the embedded artifacts and the build manifest

The verifier runs once in the builder stage, again after copying into the final image, and once more from the completed image in GitHub Actions.

## Runtime boundary

T1-03 deliberately leaves runtime delivery unchanged:

- `/client.html` still retrieves the official `testclient-new.html`
- official client assets are still proxied at runtime
- `/opt/pokemon-showdown-client` is not yet exposed by the launcher

Local serving is introduced separately in T1-04. Default cutover and removal of the broad runtime proxy remain T1-05.

T1-03 does not change `data/`, `sim/`, normalized IDs, battle protocol messages, `/choose`, `/team`, team Import/Export, foul-play inputs, or Rust `poke-engine` inputs.
