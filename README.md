# shurl — MLH PE Hackathon 2026 Submission

This repository is my solution / implementation / submission for **MLH PE Hackathon 2026**.

The MLH PE Hackathon 2026 was built around a compelling challenge: take a URL shortener template and push it to production-grade quality by completing a series of **Production Engineering quests** — covering reliability, scalability, incident response, and documentation. With five non-cash prizes on the line, I set my sights on the **Scalability Quest** and its top prize: a **Raspberry Pi 5 Starter Kit**. The goal wasn't just to build something that *works* — it was to build something that *scales*.

- **Template repo**: [MLH-Fellowship/PE-Hackathon-Template-2026](https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026)
- **Demo video**: *TODO* (YouTube link placeholder)

## Table of contents

- [Features](#features)
- [Technologies](#technologies)
- [Using the live app](#using-the-live-app)
- [Run locally](#run-locally)
  - [Option A: Flask only (Bronze)](#option-a-flask-only-bronze)
  - [Option B: Full stack with Docker Compose (Silver/Gold)](#option-b-full-stack-with-docker-compose-silvergold)
  - [Seed data (optional)](#seed-data-optional)
- [Quest focus: Scalability](#quest-focus-scalability)
- [Contributing](#contributing)
- [Support](#support)
- [Acknowledgements](#acknowledgements)

## Features

- **Live production deployment** on a real domain: `https://shurl.kdmarc.xyz` (TLS via Nginx)
- **Health check endpoint**: `GET /health` → `{"status":"ok"}`
- **URL shortener core flow**:
  - **Create short links**: `POST /urls` generates a unique 6‑char `short_code`
  - **Redirect**: `GET /<short_code>` returns **302** (or **404** if missing/inactive)
- **API-first CRUD** (JSON):
  - **Users**: `GET/POST /users`, `GET/PUT/DELETE /users/<id>` with pagination
  - **URLs**: `GET/POST /urls`, `GET/PUT/DELETE /urls/<id>` with pagination + filters (`user_id`, `is_active`)
  - **Events**: `GET/POST /events` for recording and listing event data (paginated)
- **Bulk user import**: `POST /users/bulk` accepts a multipart CSV upload (same format as hackathon seed files)
- **Redirect caching with observability**:
  - Redis-backed redirect cache (when `REDIS_URL` is set)
  - `X-Cache: HIT|MISS` header on redirects
  - Cache invalidation on URL updates/deletes
- **Scale-ready container layout**: multiple app containers behind an Nginx upstream (see `compose.yaml` + scalability docs)

## Technologies

- **API**: Flask
- **Database**: PostgreSQL (Peewee ORM)
- **Cache**: Redis
- **Edge / routing**: Nginx
- **Load testing**: k6
- **Python deps**: `uv`
- **Containers**: Docker + Compose

## Using the live app

This is a real running instance while it’s hosted: you can use it to shorten URLs.

- **Base URL**: `https://shurl.kdmarc.xyz`
- **Example endpoint**: `GET /users?page=1` → [`https://shurl.kdmarc.xyz/users?page=1`](https://shurl.kdmarc.xyz/users?page=1)

**How it works (high level):**

- **No authentication**: create a user via the `users` endpoint.
- **Shorten a URL**: use the `urls` endpoint to create a short code for a long URL.
- **Redirect**: visit `https://shurl.kdmarc.xyz/<short_code>` and the server returns a redirect.

**Request payloads (examples):**

- **Create a user** (`POST /users`)

```bash
curl -sS -X POST "https://shurl.kdmarc.xyz/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "yourname",
    "email": "you@example.com"
  }'
```

Example response:

```json
{
  "created_at": "2026-04-06T15:40:01",
  "email": "you@example.com",
  "id": 1,
  "username": "yourname"
}
```

- **Create a short URL** (`POST /urls`)

```bash
curl -sS -X POST "https://shurl.kdmarc.xyz/urls" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "original_url": "https://example.com/some/very/long/url",
    "title": "Example link"
  }'
```

Example response:

```json
{
  "created_at": "2026-04-06T15:40:10",
  "id": 1,
  "is_active": true,
  "original_url": "https://example.com/some/very/long/url",
  "short_code": "Ti5sD0",
  "title": "Example link",
  "updated_at": "2026-04-06T15:40:10",
  "user_id": 1
}
```

- **Use the short code** (`GET /<short_code>`)

```bash
curl -sS -D - -o /dev/null "https://shurl.kdmarc.xyz/Ti5sD0"
```

Example response (headers):

```text
HTTP/2 302
location: https://example.com/some/very/long/url
x-cache: HIT
```

- **List URLs (paginated + filters)** (`GET /urls?page=1&per_page=20&user_id=1&is_active=true`)

```bash
curl -sS "https://shurl.kdmarc.xyz/urls?page=1&per_page=20&user_id=1&is_active=true"
```

Example response:

```json
{
  "has_next": false,
  "has_prev": false,
  "items": [
    {
      "created_at": "2026-04-06T15:40:10",
      "id": 1,
      "is_active": true,
      "original_url": "https://example.com/some/very/long/url",
      "short_code": "Ti5sD0",
      "title": "Example link",
      "updated_at": "2026-04-06T15:40:10",
      "user_id": 1
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 1,
  "total_pages": 1
}
```

## Run locally

### Option A: Flask only (Bronze)

Prereqs:

- `uv` installed (see [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/))
- A local Postgres you can connect to (or use Docker Compose below)

From repo root:

```bash
cp .env.example .env
uv run run.py
```

Verify:

```bash
curl http://127.0.0.1:5000/health
```

### Option B: Full stack with Docker Compose (Silver/Gold)

This runs **Nginx (80/443)** + multiple app containers + Postgres + Redis.

Note: this Compose setup is designed for a deployed VM with TLS certs at `/etc/letsencrypt` for `shurl.kdmarc.xyz`. For local development, **Option A** is the simplest path.

From repo root:

```bash
cp secrets/postgres_password.txt.example secrets/postgres_password.txt

# Foreground (logs)
docker compose up --build

# Or detached (common on a VM)
# docker compose up -d --build
```

Verify (local):

```bash
docker compose exec server-1 python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

### Seed data (optional)

If you have the hackathon seed files (place them in `data/`), you can load them into Postgres.

Requires:

- `data/users.csv`
- `data/urls.csv`
- `data/events.csv`

With Compose running:

```bash
docker compose exec server-1 python scripts/load_seed_csv.py
```

## Quest focus: Scalability

The repo includes write-ups and commands for the Scalability quest tiers:

- **Bronze**: [`docs/scalability-bronze.md`](docs/scalability-bronze.md)
- **Silver**: [`docs/scalability-silver.md`](docs/scalability-silver.md)
- **Gold**: [`docs/scalability-gold.md`](docs/scalability-gold.md)

## Contributing

Issues and pull requests are welcome.

- **Bug reports**: include repro steps, expected vs actual behavior, and any relevant logs.
- **Feature ideas**: describe the use case first (the “why”), then propose a minimal solution.
- **Code changes**: keep PRs small and focused; update docs when behavior changes.

## Support

If you find this project helpful or interesting, consider supporting me:

[☕ Buy me a coffee](https://buymeacoffee.com/gideonadeti)

## Acknowledgements

- **MLH PE Hackathon 2026** for the challenge and Production Engineering quests.
- The original template: [MLH-Fellowship/PE-Hackathon-Template-2026](https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026)
- Open-source tooling that made this build possible: Flask, Peewee, Postgres, Redis, Nginx, Docker, k6, and `uv`.
