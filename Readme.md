# AgriSense

**Mandi price intelligence + farmer-buyer marketplace + a Hindi/Hinglish AI agent.**

A 15-day, 1-hour-per-day backend teaching project built with **FastAPI, PostgreSQL (SQLModel), Redis and LLM tool calling**. It is DB-heavy on purpose: indexing, partitioning, rollups, caching, row locking and rate limiting, with sharding covered as a concept.

> Made by E-Skills Web LLP for intermediate students. The full day-by-day guide (concepts, code walkthroughs, daily tests) is the companion PDF: _AgriSense 15-Day Backend Guide_.

---

## What it does

- **Prices:** 30 mandis, 20 crops, about 3 lakh synthetic daily price records (seeded, so every student gets the same data). Latest price, history, monthly trend and cross-mandi ranking.
- **Marketplace:** farmers list produce, buyers purchase it, and stock is never oversold (row locking).
- **Crowd-sourced prices:** farmers can submit today's price, under a strict token-bucket limit.
- **AI agent:** ask "Indore me gehu ka bhaav kya hai?" and the agent calls real tools against the database. Works offline with a built-in FakeLLM, or with Gemini.

## Concepts covered

| Area             | What you build                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| Layered design   | Router -> Service -> Database, plus AI layers on top                                              |
| Auth             | bcrypt hashing, JWT, roles (farmer / buyer / admin), 401 vs 403                                   |
| Rate limiting    | Fixed window, sliding window log, token bucket (Redis Lua), per-user identity                     |
| Database depth   | `EXPLAIN ANALYZE`, composite indexes, N+1, range partitioning, materialized views, `LAG` / `RANK` |
| Caching          | Cache-aside with TTL and invalidation (`X-Cache: HIT/MISS`)                                       |
| Concurrency      | Race condition demo, `SELECT ... FOR UPDATE`                                                      |
| Sharding (intro) | Hash routing, skew, cross-shard queries                                                           |
| AI agent         | Provider-neutral LLM layer, tool registry, agent loop, token quota, audit log                     |
| Performance      | Locust load test, p95 latency, before/after optimisation                                          |
| Quality          | pytest smoke tests                                                                                |

## Architecture

```
Client -> Timing middleware -> Rate limiter (Redis) -> Auth (JWT + roles) -> Router -> Service -> PostgreSQL / Redis
                                                                              |
                                                                              +-> Agent loop -> LLM client (Gemini / FakeLLM)
                                                                                     |
                                                                                     +-> Tool registry -> Service -> PostgreSQL
```

## Tech stack

FastAPI, SQLModel (SQLAlchemy 2 + Pydantic), PostgreSQL 16, Redis 7, bcrypt, PyJWT, google-genai, pytest, Locust, Docker Compose.

## Project structure

```
agrisense/
├── app/
│   ├── main.py              # FastAPI app, middleware, routers
│   ├── config.py            # settings from .env
│   ├── database.py          # engine, session, table creation
│   ├── models.py            # tables: Market, Crop, PriceRecord, User, Listing, Order, AgentRun
│   ├── schemas.py           # request/response shapes
│   ├── security.py          # bcrypt + JWT
│   ├── deps.py              # get_current_user, require_role
│   ├── ratelimit.py         # fixed / sliding / token bucket
│   ├── redis_client.py
│   ├── cache.py             # cache-aside helpers
│   ├── routers/             # auth, catalog, prices, analytics, listings, agent
│   ├── services/            # price_service (SQL queries)
│   └── agent/               # llm.py, prompts.py, tools.py, loop.py, quota.py
├── scripts/                 # seed, seed_users, hammer, explain, partition,
│                            # create_rollups, race_test, shard_demo, llm_ping, add_indexes
├── tests/test_api.py        # 10 smoke tests
├── locustfile.py
├── docker-compose.yml
└── requirements.txt
```

## Quick start

Requirements: Python 3.11+, Docker.

```bash
git clone <your-repo-url> agrisense && cd agrisense
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

docker compose up -d               # Postgres 16 + Redis 7
cp .env.example .env               # or create .env, see below

python -m scripts.seed             # ~3 lakh price records (1-2 min)
python -m scripts.seed_users       # demo users + sample listings
python -m scripts.partition        # Day 7: quarterly partitions
python -m scripts.create_rollups   # Day 8: monthly materialized view

uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** (Swagger UI).

### `.env`

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/agrisense
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me
READ_LIMIT_PER_MIN=60

# AI agent: fake (offline) or gemini
LLM_PROVIDER=fake
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-latest
AGENT_DAILY_TOKEN_QUOTA=20000
```

## Demo accounts

| Role   | Email                 | Password  |
| ------ | --------------------- | --------- |
| admin  | admin@agrisense.dev   | admin123  |
| farmer | farmer@agrisense.dev  | farmer123 |
| farmer | farmer2@agrisense.dev | farmer123 |
| buyer  | buyer@agrisense.dev   | buyer123  |

For class use only. Never ship default credentials.

## API overview

| Method | Path                               | Access          | Limit / safety                          |
| ------ | ---------------------------------- | --------------- | --------------------------------------- |
| GET    | `/health`                          | public          | -                                       |
| GET    | `/markets`, `/crops`               | public          | -                                       |
| GET    | `/prices`                          | public          | fixed window, 60/min                    |
| GET    | `/prices/latest`                   | public          | sliding window 60/min + 5 min cache     |
| POST   | `/prices/submit`                   | farmer, admin   | token bucket, 5 per 60 s                |
| GET    | `/prices/trend`, `/prices/compare` | public          | sliding window, 60/min                  |
| POST   | `/admin/refresh-rollups`           | admin           | -                                       |
| POST   | `/auth/register`, `/auth/login`    | public          | -                                       |
| GET    | `/auth/me`                         | login           | -                                       |
| POST   | `/listings`                        | farmer          | -                                       |
| GET    | `/listings`, `/listings/mine`      | public / farmer | -                                       |
| POST   | `/listings/{id}/buy`               | buyer           | row lock (`FOR UPDATE`)                 |
| POST   | `/agent/chat`                      | login           | token bucket 10/min + daily token quota |
| GET    | `/agent/usage`, `/agent/runs`      | login           | -                                       |

Status codes: `400` bad input, `401` not logged in, `403` wrong role, `404` not found, `409` conflict (duplicate email, not enough stock), `422` validation, `429` rate limit or quota, `502` AI service down.

## The AI agent

```
POST /agent/chat  ->  guards (login, rate limit, size, quota)
                  ->  agent loop (max 5 steps)
                  ->  LLM client (Gemini or FakeLLM)
                  ->  tool registry (allow-listed args, user taken from the JWT, never from the LLM)
                  ->  services -> PostgreSQL
```

Tools: `get_mandi_prices`, `compare_markets`, `price_trend`, `list_my_produce`.

Every run is stored in `agent_runs` (question, tools used, tokens, latency, status). If the LLM provider fails, the API returns `502` and the failure is logged.

**FakeLLM** picks tools by keyword, so the whole agent loop runs without an API key or internet. It is not as smart as a real model. To use Gemini, set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY`, then run `python -m scripts.llm_ping` to verify.

## Testing

```bash
pytest -q                                           # 10 smoke tests

python -m scripts.hammer "/prices?limit=1" 65       # rate limit: 60 x 200, 5 x 429
python -m scripts.race_test                         # 20 buyers, 500 kg: 5 orders, 15 x 409
python -m scripts.explain --index                   # query plans
python -m scripts.shard_demo                        # shard skew demo

locust -f locustfile.py --headless -u 50 -r 10 -t 30s --host http://localhost:8000
```

Tests expect `seed`, `seed_users` and `create_rollups` to have been run, with Postgres and Redis up.

## Load test result (one dev machine, 50 users)

| Endpoint          | Before avg / p95 (ms) | After avg / p95 (ms) |
| ----------------- | --------------------- | -------------------- |
| `/prices`         | 173 / 330             | 14 / 48              |
| `/prices/compare` | 329 / 550             | 15 / 23              |
| `/prices/latest`  | 26 / 93               | 12 / 43              |
| `/prices/trend`   | 20 / 53               | 10 / 16              |
| **Overall**       | **88 / 360**          | **12 / 29**          |

The fix was a `(crop_id, price_date DESC, id)` index, filtering by `crop_id` instead of `lower(name)`, and a CTE in the compare query. Your numbers will differ; the direction is what matters. Raise `READ_LIMIT_PER_MIN` while load testing, otherwise rate limiting produces 429s.

## Known limitations

- The sliding-window limiter does check and add in separate steps, so a tiny race exists. Rewriting it in Lua is a good exercise.
- The fixed-window test can look odd if the minute changes mid-test. That is the algorithm's boundary-burst weakness, not a bug.
- The race test without the lock is non-deterministic.
- Rollups are refreshed manually (`/admin/refresh-rollups`). Use a scheduler in production.
- Tables are created with `create_all`. Use Alembic migrations in production.
- The Gemini adapter was verified offline only. Run `llm_ping` with your own key before relying on it.

## Roadmap ideas

Alembic migrations, scheduled rollup refresh, read replica, background workers, conversation memory for the agent, streaming responses, a React/Next.js front end, CI with GitHub Actions.

## License

MIT (add a `LICENSE` file before publishing).
