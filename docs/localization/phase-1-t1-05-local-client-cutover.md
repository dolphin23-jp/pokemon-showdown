# Phase 1 T1-05: default local client cutover

T1-05 makes the pinned `pokemon-showdown-client` build the default browser client and retires the launcher's runtime dependency on the official client host.

## Default entry

`/client.html` now reads the pinned entry from:

```text
/opt/pokemon-showdown-client/play.pokemonshowdown.com/testclient-new.html
```

No environment switch is required. `ENABLE_PINNED_CLIENT` is no longer consulted.

The T1-04 entry remains as a compatibility alias:

```text
/local-client/testclient-new.html
```

## Local static routes

The launcher serves only explicit pinned-client paths:

- `/data/`
- `/js/`
- `/src/`
- `/style/`
- `/config/config.js`
- `/config/testclient-key.js` when present
- `/favicon.ico`
- `/favicon-256.png`
- `/local-client/` compatibility assets

Unknown paths return HTTP 404. They are not forwarded to `play.pokemonshowdown.com`.

The `/showdown` HTTP and WebSocket routes remain the only proxy routes, and they target the local Pokémon Showdown server on `127.0.0.1`.

## Entry rewriting

The pinned test-client HTML is patched at response time to:

- inject the same-origin `/showdown` server configuration
- keep browser-only `/trn <name>,0,` login behavior
- send Japanese settings once after named login
- load generated `config/config.js` from the local image
- load the favicon and explicit Pokédex mini scripts from the same origin
- keep data and JavaScript error fallbacks on the same origin
- use the current origin as `Net.defaultRoute`

The cutover does not rewrite normalized IDs, team data, battle choices, or protocol payloads.

## Retired runtime paths

The launcher no longer contains or calls:

- `https.get()` for official `testclient-new.html`
- `OFFICIAL_CLIENT_HOST`
- the broad official-client proxy fallback
- official-client redirect rewriting

The application image still downloads the explicitly pinned Git commit during Docker build. That build-time fetch is verified separately and is not a runtime dependency.

## Access and caching

All client routes remain behind the existing access-token gate when configured.

- entry HTML: `Cache-Control: no-store`
- pinned static files: one-year immutable cache
- local responses: `X-Pokemon-Showdown-Client-Source: pinned-local`
- all local client responses: `X-Content-Type-Options: nosniff`

Only `GET` and `HEAD` are accepted for client files. Traversal, encoded dot segments, backslashes, directories, and files outside the pinned roots are rejected.

## Validation

T1-05 verifies:

- `runtime_delivery_changed: true` in the pin manifest
- absence of the retired official runtime markers
- `/client.html` is local even when `ENABLE_PINNED_CLIENT=0`
- representative generated JS, CSS, and config files are served locally
- no official-host script, image, or stylesheet references remain in the patched entry
- the T1-04 alias remains functional
- unknown paths are 404 rather than proxied
- browser rendering succeeds with DNS for `play.pokemonshowdown.com` deliberately disabled
- the four mandatory foul-play and BSS regression tests still pass

T1-05 does not modify `data/`, `sim/`, normalized IDs, battle protocol messages, `/choose`, `/team`, team Import/Export, foul-play inputs, or Rust `poke-engine` inputs.
