# Service API

## What this is

This is a small FastAPI service backed by Postgres through a local Supabase stack.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Supabase CLI](https://supabase.com/docs/guides/local-development/cli/getting-started)

## Run it

From a fresh clone, run these commands in order:

```sh
cp .env.example .env
supabase start
supabase db reset
uv sync
uv run python -m service_api
```

The local server reloads when Python source files change. Open <http://127.0.0.1:8000/docs>, select **Authorize**, and enter `local-dev-key` to call the loan endpoint.

## Develop

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
uv run ty check
```

Create and apply a database migration with:

```sh
supabase migration new <name>
supabase db reset
```
