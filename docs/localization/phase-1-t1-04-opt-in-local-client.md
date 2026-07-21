# Phase 1 T1-04: opt-in local client route

T1-04 exposes the pinned client build through a same-origin static route without changing the default browser experience.

## Activation

The route is disabled by default. Set:

```text
ENABLE_PINNED_CLIENT=1
```

The entry point then becomes available at:

```text
/local-client/testclient-new.html
```

The complete static prefix is:

```text
/local-client/
```

The client files are read from the T1-03 image location:

```text
/opt/pokemon-showdown-client/play.pokemonshowdown.com
```

`PINNED_CLIENT_ROOT` may override the client root for tests or development.

## Default behavior

T1-04 does not change `/client.html`.

Without the environment switch:

- `/client.html` still retrieves and patches the official `testclient-new.html`
- unmatched client assets are still proxied from `play.pokemonshowdown.com`
- `/local-client/...` returns HTTP 404 after authentication

The default cutover and removal of the broad official-client proxy remain T1-05.

## Local entry patch

The local `testclient-new.html` receives the same display-side connection behavior as the existing official entry:

- same-origin server configuration
- WebSocket prefix `/showdown`
- browser-only `/trn <name>,0,` login
- one-shot `/updatesettings {"language":"japanese"}` after named login
- unchanged localStorage key and player-name sanitization

The test client's absolute polyfill reference is rewritten from `/js/...` to `/local-client/js/...`. Other repository-relative CSS, JavaScript, data, and source references naturally remain under the local static prefix.

## Security and HTTP behavior

The opt-in route:

- remains behind the existing access-token cookie gate
- accepts only `GET` and `HEAD`
- rejects decoded dot segments, backslashes, null bytes, directories, and paths outside the pinned client root
- sends `X-Content-Type-Options: nosniff`
- identifies local responses with `X-Pokemon-Showdown-Client-Source: pinned-local`
- serves the entry HTML with `Cache-Control: no-store`
- serves immutable pinned assets with a one-year immutable cache policy

## Runtime integration

The Docker image sets a Node preload module:

```text
--require=/app/scripts/pinned-client-preload.js
```

The preload is a no-op for Pokémon Showdown server and build processes. It wraps `http.createServer` only when the active Node entry point is `launcher-server.js`, so server compilation, team packing, foul-play, and Rust `poke-engine` inputs remain isolated.

## Validation

T1-04 adds an integration test using a temporary client fixture. It verifies:

- disabled-by-default behavior
- access-gate preservation
- patched local entry output
- Japanese settings and browser `/trn` behavior
- local JavaScript and CSS delivery
- `HEAD` support
- unsupported-method rejection
- path-traversal rejection

GitHub Actions also starts a complete opt-in container, fetches the real pinned client entry and compiled asset, confirms `/client.html` still uses the existing official path, and captures an iPad-sized local-client screenshot.

T1-04 does not modify `data/`, `sim/`, normalized IDs, battle protocol messages, `/choose`, `/team`, team Import/Export, foul-play inputs, or Rust `poke-engine` inputs.
