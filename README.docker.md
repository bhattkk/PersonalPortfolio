# Docker Compose Portfolio App

Run the portfolio stack with Postgres, Redis, Telegram bot, kite-portfolio, stocks-refdata, and kite-market-data.

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
   - The bot will send you a login URL (from kite-portfolio via Redis).
   - Open the URL in a browser, sign in to Kite, and copy the `request_token` from the redirect URL.
   - Send `/token <request_token>` to the bot.
   - kite-portfolio will save the session to Postgres (valid ~24h). Other services (stocks-refdata, kite-market-data) use the same token.

4. **Optional: run refdata once on startup**
   Set `REFDATA_RUN_ON_START=1` in `.env` so instruments and fundamentals are fetched when stocks-refdata starts (otherwise it runs at midnight UTC).

## Services

| Service          | Role |
|------------------|------|
| postgres         | Session, instruments, fundamentals, portfolio snapshots |
| redis            | Cache, stream `telegram:outbound`, reply context, commands pub/sub |
| telegram         | Single Telegram bot; consumes outbound stream; handles /login, /token, /watchlist, /refresh_sd, /help, /ping |
| kite-portfolio   | Subscribes to `telegram:commands`; handles login, watchlist, refresh_sd; pushes login URL and report to stream |
| stocks-refdata   | Midnight job: Kite instruments (EQ+INDEX) + yfinance fundamentals → Postgres + Redis |
| kite-market-data | Timer: Kite LTP → Redis (`market:ltp:*`) |

## Data flow

- **Login**: You send `/login` → telegram publishes `login` → kite-portfolio pushes login URL to stream with reply_context_id → telegram sends URL to you → you send `/token <token>` → telegram writes token to Redis context → kite-portfolio reads it and saves session to Postgres.
- **Watchlist**: `/watchlist` → kite-portfolio fetches holdings/positions, saves snapshot to Postgres, builds CSV, pushes to stream → telegram sends you the CSV.
- **Static data**: `/refresh_sd` → kite-portfolio fetches instruments (EQ+INDEX) and upserts to Postgres. stocks-refdata runs the same plus yfinance at midnight.

## Volumes

- `postgres_data`: Postgres data
- `redis_data`: Redis persistence (appendonly)

Schema is applied automatically from `migrations/01_init.sql` on first Postgres start.
