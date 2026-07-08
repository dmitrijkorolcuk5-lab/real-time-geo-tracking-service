# Real-Time Geo-Tracking & Alerting Service

FastAPI backend for ingesting device locations in real time, matching them against per-user geozones with PostGIS, and broadcasting location updates and alerts over WebSockets.

## What It Does

- Accepts single and batched location updates.
- Stores the latest location per `(user_id, device_id)`.
- Lets users create, read, update, and delete circular geozones.
- Matches incoming locations against active geozones using PostGIS `ST_DWithin`.
- Broadcasts location updates and geozone alerts to all active WebSocket sessions for the correct user.
- Simulates high load with an async generator for 10,000 devices.

## Architecture

```text
HTTP clients -> FastAPI validation
             -> sharded bounded asyncio queues
             -> multiple batch workers
             -> bulk upsert latest_device_locations
             -> batch PostGIS geozone matching
             -> Redis Pub/Sub
             -> WebSocket manager
             -> multiple sessions per user
```

## Technologies

- Python 3.10+
- FastAPI
- Async SQLAlchemy
- asyncpg
- PostgreSQL + PostGIS
- Redis
- Docker and docker-compose
- WebSockets
- httpx for the load generator

## Run with Docker

Copy the environment template first:

```bash
cp .env.example .env
```

Then start the stack:

```bash
docker compose up --build
```

The stack reads all credentials and environment-specific values from `.env`. The example file includes PostgreSQL, Redis, API, queue, and worker settings. A clean local startup looks like this:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Migrations

Run migrations manually when needed:

```bash
alembic upgrade head
```

Inside Docker, migrations run automatically before the API server starts.

## Run Tests

Run the test suite locally:

```bash
python -m pytest -q
```

Or inside the API container:

```bash
docker compose exec api python -m pytest -q
```

## Health Check

```bash
curl http://localhost:8000/health
```

The response reports API, database, Redis, and queue status.

It now also reports the configured worker count, total queue size, and per-shard queue sizes.

## Create a Geozone

```bash
curl -X POST http://localhost:8000/api/v1/geozones \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -d '{"name":"Warehouse Zone","latitude":49.8397,"longitude":24.0297,"radius_m":150,"is_active":true}'
```

## Send One Location Update

```bash
curl -X POST http://localhost:8000/api/v1/locations \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -d '{"device_id":"device-1","latitude":49.8397,"longitude":24.0297,"timestamp":"2026-07-06T12:00:00Z"}'
```

## Send Batch Location Updates

```bash
curl -X POST http://localhost:8000/api/v1/locations/batch \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -d '{"locations":[{"device_id":"device-1","latitude":49.8397,"longitude":24.0297,"timestamp":"2026-07-06T12:00:00Z"}]}'
```

## Connect to WebSocket

Use either the query parameter or the `X-User-Id` header:

```text
ws://localhost:8000/api/v1/ws?user_id=user-123
```

## Demo Page

Open the Jinja demo at [http://localhost:8000/](http://localhost:8000/). It provides a simple server-rendered UI for connecting a WebSocket, entering a `user_id`, and watching location updates and geozone alerts stream in.

Example message formats:

```json
{
  "type": "location_update",
  "device_id": "device-123",
  "latitude": 49.8397,
  "longitude": 24.0297,
  "timestamp": "2026-07-06T12:00:00Z"
}
```

```json
{
  "type": "geozone_alert",
  "user_id": "user-123",
  "device_id": "device-123",
  "geozone_id": "zone-id",
  "geozone_name": "Warehouse Zone",
  "latitude": 49.8397,
  "longitude": 24.0297,
  "timestamp": "2026-07-06T12:00:00Z"
}
```

## Run the 10,000-Device Generator

The generator uses a bounded concurrency limit so it does not create unlimited concurrent requests.

```bash
python generator.py --devices 10000 --batch-size 500 --interval 3 --concurrency 20 --api-url http://localhost:8000
```

Useful options:

- `--devices 10000` controls the number of simulated devices.
- `--batch-size 500` splits requests into manageable chunks.
- `--interval 3` sets the delay between ticks.
- `--concurrency 20` caps the number of concurrent batch requests.
- `--api-url http://localhost:8000` points the generator at the API.

The generator is intentionally bounded by `--concurrency` so it can safely simulate 10,000 devices without opening unbounded concurrent requests.

## Worker Sharding

Location ingestion is sharded across `LOCATION_WORKER_COUNT` bounded queues. Each incoming event is routed by a stable SHA-256 hash of `(user_id, device_id)`, so the same device for the same user always lands on the same shard.

This preserves per-device ordering as much as the queue allows while distributing load across multiple workers.

## Batch Geozone Matching

The worker now deduplicates the latest location per `(user_id, device_id)` and performs geozone matching with one batch query per processed batch. The repository uses a `VALUES` table joined against `geozones` with `ST_DWithin`, so the old N+1 query pattern is removed while keeping user isolation strict.

## User Isolation

- Geozones are isolated by `user_id`.
- Latest device locations are isolated by `(user_id, device_id)`.
- Batch deduplication is also scoped by `(user_id, device_id)`.
- WebSocket broadcasts are routed only to sessions registered for the matching user.

## Known Trade-Offs

- Alerts are emitted for matching locations as they are processed; there is no enter/exit state machine yet.
- The WebSocket sender prioritizes alerts over stale location updates, and it may drop queued location updates if a client is slow.
- The service uses a simplified header/query-based user identity model instead of OAuth.

## Notes

- The API expects `X-User-Id` for simplified mock authentication.
- The project uses async SQLAlchemy with `asyncpg`.
- `latest_device_locations` is keyed by `(user_id, device_id)`.
- The health check requires a live database and Redis connection to report `ok`.
