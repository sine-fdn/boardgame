# Deployment

Hosting the ÖPGV Boardgame (oTree) with Docker Compose.

## What runs

Two containers:

- `otree` — the game itself, serving on port 8000 internally.
- `postgres` — a bundled Postgres database, so the stack is self-contained
  out of the box. It's optional: `otree` can be pointed at any Postgres
  instead (see [Database](#database)), or at no database at all, in which
  case it falls back to a SQLite file inside the container.

`otree` is pulled as a pre-built image (`ghcr.io/sine-fdn/boardgame`); it is
not built locally by `docker-compose.yml`.

## Prerequisites

- Docker Engine 20.10+ with the Compose v2 plugin (`docker compose version`)
- read access to the container registry, if the package is private (see
  [Registry access](#registry-access))

## Quick start

The steps below use a local `.env` file, the simplest option for a single
server. Any other way of setting the same variables works too — see
[Environment variables](#environment-variables).

```sh
cp .env.example .env
# fill in the mandatory variables (see the table below)
docker compose pull
docker compose up -d
```

Check it came up:

```sh
docker compose ps
curl -I http://localhost:8000/
```

## Environment variables

All variables must be set wherever `docker compose` runs, however that
environment provides them (a local `.env` file, CI/CD secrets, systemd, ...).
`.env.example` documents each one; the table below is the summary.

| Variable               | Required  | Default                       | Purpose                                       |
| ---------------------- | --------- | ----------------------------- | --------------------------------------------- |
| `IMAGE`                | no        | `ghcr.io/sine-fdn/boardgame`  | image repository                              |
| `IMAGE_TAG`            | no        | `latest`                      | image tag — the rollback lever                |
| `OTREE_HOST_PORT`      | no        | `8000`                        | host port the app is published on             |
| `OTREE_BIND_ADDR`      | no        | `0.0.0.0`                     | host interface to publish on                  |
| `OTREE_ADMIN_USERNAME` | no        | `admin`                       | username for the oTree admin interface        |
| `OTREE_ADMIN_PASSWORD` | **yes**   | –                             | secret; password for the admin interface      |
| `OTREE_SECRET_KEY`     | **yes**   | –                             | secret; Django session/CSRF signing key       |
| `OTREE_REST_KEY`       | **yes**   | –                             | secret; authenticates REST API callers        |
| `DATABASE_URL`         | no        | ephemeral SQLite in-container | where oTree stores its data                   |
| `POSTGRES_USER`        | **yes**\* | –                             | bundled Postgres container's user             |
| `POSTGRES_PASSWORD`    | **yes**\* | –                             | secret; bundled Postgres container's password |
| `POSTGRES_DB`          | **yes**\* | –                             | bundled Postgres container's database name    |

\* `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` are required by Compose
even if you don't intend to use the bundled Postgres at all — see
[Known limitations](#known-limitations).

`OTREE_ADMIN_PASSWORD`, `OTREE_SECRET_KEY`, and `OTREE_REST_KEY` are
deliberately mandatory: `docker compose up -d` aborts if any is missing,
before any running container is replaced. `otree` reads them at process
startup and would otherwise crash immediately (the first two) or silently
reject every REST API call (the third).

### Secrets

Generate fresh values rather than reusing the examples in `.env.example`:

```sh
openssl rand -base64 24    # OTREE_ADMIN_PASSWORD, POSTGRES_PASSWORD
openssl rand -hex 32       # OTREE_REST_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"  # OTREE_SECRET_KEY
```

`OTREE_REST_KEY` must be the identical value configured in the `oepgv-docs`
repo's own `OTREE_REST_KEY` — that site calls this app's REST API to run
sessions of the learning game.

## Ports

`OTREE_HOST_PORT` and `OTREE_BIND_ADDR` control the only port published to
the host. The port *inside* the `otree` container is fixed at 8000 (see the
`Dockerfile`'s `EXPOSE`).

The bundled `postgres` service currently publishes **no** port at all — it's
reachable only from `otree` over Compose's internal network, on the same
host. See [Known limitations](#known-limitations) if you need to reach it
from outside that network.

## Database

`DATABASE_URL` is deliberately independent of everything else in this file —
point it at whichever database this deployment actually uses:

- the bundled `postgres` service (`postgresql://<user>:<password>@postgres:5432/<db>`,
  matching `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`),
- an external managed database (e.g. Neon),
- or leave it unset, and oTree falls back to a SQLite file inside the
  container — which is lost on every restart or redeploy, since the
  container's filesystem isn't persisted. Fine for a quick smoke test, not
  for anything you want to keep.

oTree creates its schema automatically on first startup against an empty
database; no separate migration step is needed.

## Known limitations

This file bundles `otree` and `postgres` together for the common case of
self-hosting the whole stack on one server. One thing currently limits
running them on separate hosts (e.g. `otree` on one server, `postgres`
elsewhere, or vice versa):

- **`postgres` has no port mapping.** As shipped, nothing outside its own
  Compose project can reach it — not a config issue, there is simply no
  network path. Add a `ports:` entry (e.g. bound to `127.0.0.1` or a
  specific private interface, never `0.0.0.0`, since Postgres has no TLS
  configured here) if you need to reach it from another host.

Separately, Compose validates every mandatory (`:?`) variable in this file
for any `docker compose` command, regardless of which service you target.
Running `docker compose up otree` on a host that only runs the app still
requires `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` to be set there
too, even though `postgres` never starts — there's no way to scope that
validation to only the targeted service. The least-friction option is
setting throwaway values for the unused variables on that host.

`otree` has no `depends_on` on `postgres`, so `docker compose up otree` alone
starts only `otree` — no `--no-deps` needed. The trade-off: if both services
run together on the same host, `otree` no longer waits for Postgres to
report healthy first. With `restart: always`, it just retries until Postgres
is reachable, so this only shows up as a few failed attempts in the logs
right after a cold start.

## Registry access

If the package is private, authenticate once per server with a classic
Personal Access Token that has only the `read:packages` scope:

```sh
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-username> --password-stdin
```

Credentials are stored in `~/.docker/config.json` for the user running
Compose. If the package is public, no login is required.

## Image tags

The CI workflow (`.github/workflows/docker-build.yml`) produces, for every
push to `main`:

- `sha-<short-commit-sha>` — immutable, one per commit, produced for
  `main`, `deployment`, and manual runs
- `latest` — moving pointer, produced **only** for `main`

`latest` makes routine updates a two-liner; the `sha-` tags make rollback
exact.

## Updating

```sh
docker compose pull
docker compose up -d
```

Compose recreates a container only if its pulled image differs.

## Rolling back

```sh
# set in your environment
IMAGE_TAG=sha-1a2b3c4
```

```sh
docker compose up -d
```

## Operating

```sh
docker compose logs -f otree      # follow logs
docker compose ps                 # status
docker compose restart otree      # restart
docker compose down                # stop (volumes are kept)
```

## Troubleshooting

**`up` fails with `<VARIABLE> is not set`** — that variable is missing or
empty wherever you set it. Nothing was changed; the previous container is
still running.

**oTree admin login fails** — check `OTREE_ADMIN_USERNAME` (defaults to
`admin`) and `OTREE_ADMIN_PASSWORD` match what's configured.

**`oepgv-docs` can't start sessions / REST calls fail** — `OTREE_REST_KEY`
here doesn't match the value configured in the `oepgv-docs` deployment.

**Data disappeared after a restart** — `DATABASE_URL` was never set, so
oTree was using the ephemeral in-container SQLite fallback. Point it at a
real database.
