# Docker Compose Portfolio App

Run the portfolio stack with Postgres, Redis, Telegram bot, **stocks**, **refdata**, and **prices**.

## Prerequisites

- Docker and Docker Compose
- Kite Connect API key and secret
- Telegram bot token and your chat ID

## Setup

1. **Copy env file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `KITE_API_KEY`, `KITE_API_SECRET`
   - `TELEGRAM_BOT_TOKEN`, `CHAT_ID`
   - `POSTGRES_PASSWORD` (optional; default `portfolio`)

2. **Start infrastructure and services**
   ```bash
   docker compose up -d
   ```

3. **First-time Kite login**
   - Open Telegram and send `/login` to your bot.
   - The bot will send you a login URL (from the **stocks** service via Redis).
   - Open the URL in a browser, sign in to Kite, and copy the `request_token` from the redirect URL.
   - Send `/token <request_token>` to the bot.
   - **stocks** saves the session to Postgres (valid ~24h). Other services (**refdata**, **prices**) use the same token.

4. **Optional: run refdata once on startup**
   Set `REFDATA_RUN_ON_START=1` in `.env` so instruments and fundamentals are fetched when **refdata** starts (otherwise it runs at midnight UTC).

## Services

| Service   | Role |
|-----------|------|
| postgres  | Session, instruments, fundamentals, portfolio snapshots, watchlist |
| redis     | Cache, stream `telegram:outbound`, reply context, commands pub/sub |
| telegram  | Single Telegram bot; consumes outbound stream; handles /login, /token, /watchlist, /refresh_sd, /help, /ping |
| stocks    | Subscribes to `telegram:commands`; handles login, watchlist, refresh_sd; pushes login URL and report to stream |
| refdata   | Midnight job: Kite instruments (EQ+INDEX) + yfinance fundamentals → Postgres + Redis |
| prices    | Timer: Kite LTP → Redis (`market:ltp:*`) |

## Data flow

- **Login**: You send `/login` → telegram publishes `login` → **stocks** pushes login URL to stream with reply_context_id → telegram sends URL to you → you send `/token <token>` → telegram writes token to Redis context → **stocks** reads it and saves session to Postgres.
- **Watchlist**: `/watchlist` → **stocks** fetches holdings/positions, saves snapshot to Postgres, builds CSV, pushes to stream → telegram sends you the CSV.
- **Static data**: `/refresh_sd` → **stocks** fetches instruments (EQ+INDEX) and upserts to Postgres. **refdata** runs the same plus yfinance at midnight.

## Volumes

- `postgres_data`: Postgres data
- `redis_data`: Redis persistence (appendonly)

Schema is applied automatically from `migrations/*.sql` on first Postgres start (e.g. `01_init.sql`, `02_watchlist.sql`).

**Already have a Postgres volume?** New SQL files are not re-run automatically. Apply `02_watchlist.sql` once, for example:

```bash
docker compose exec -T postgres psql -U portfolio -d portfolio -f /docker-entrypoint-initdb.d/02_watchlist.sql
```

(Or run the same SQL from `migrations/02_watchlist.sql` with any `psql` client.)
