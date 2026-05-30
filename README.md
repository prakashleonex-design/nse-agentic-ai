# NSE Agentic Trader

Starter project for building an agentic intraday trading assistant for NSE index trading with Angel One SmartAPI.

This project is intentionally conservative:

- Paper trading is the default.
- Live order placement is blocked unless explicitly enabled.
- Strategy logic is deterministic; the AI layer explains and challenges trades instead of inventing orders.
- Risk checks run before every trade.

## What This Is

An extensible skeleton for:

1. Reading market snapshots from Angel SmartAPI or local sample data.
2. Generating NIFTY/BANKNIFTY intraday signals.
3. Passing signals through a risk manager.
4. Asking an agent layer for a structured trade review.
5. Executing in paper mode by default.
6. Journaling every decision.

## Strategy Scope

The system is being shaped around six strategy families:

- Scalping or momentum.
- Breakout.
- Option buying.
- Option selling.
- Trend following.
- Mean reversion.

Each strategy must produce a structured trade idea: symbol, option contract when applicable, entry, stop loss, target, confidence, reason, invalidation condition, and expected holding time. The assistant reviews and challenges these ideas before any broker action.

Option buying and breakout/momentum are the first practical implementation targets because risk is naturally capped to premium paid. Option selling is research and paper-only until margin checks, defined-risk spreads, emergency exits, and stricter live controls are implemented.

## What This Is Not

This is not a profitable trading system, a financial advisor, or a plug-and-play live bot. Use it as engineering infrastructure and test every strategy with historical data, paper trading, and tiny live size before risking real capital.

## Project Layout

```text
src/nse_agentic_trader/
  agent/        AI review layer
  broker/       Angel SmartAPI and paper broker adapters
  risk/         Position sizing, drawdown, kill-switch checks
  strategy/     Example opening-range breakout strategy
  app.py        CLI entry point
  config.py     Environment-driven settings
  models.py     Shared dataclasses
```

## Quick Start

```powershell
cd work\nse-agentic-trader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m nse_agentic_trader.app --mode paper --symbol NIFTY
```

Run a specific strategy:

```powershell
python -m nse_agentic_trader.app --mode paper --symbol NIFTY --strategy opening_range_breakout
```

Available starter strategy names:

- `opening_range_breakout`
- `scalping_momentum`
- `option_buying`
- `option_selling`
- `trend_following`
- `mean_reversion`

## Angel SmartAPI Setup

Create a `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Fill in:

```text
ANGEL_CLIENT_CODE=
ANGEL_PASSWORD=
ANGEL_API_KEY=
ANGEL_TOTP_SECRET=
```

Live order placement also requires:

```text
TRADING_MODE=live
ALLOW_LIVE_ORDERS=true
```

Both are required by design.

## Suggested Build Path

1. Keep `TRADING_MODE=paper`.
2. Replace sample market data with Angel websocket candles.
3. Backtest your actual index strategy.
4. Add broker-specific instrument tokens for NIFTY/BANKNIFTY options.
5. Add alerts and manual approval.
6. Enable live mode only after long paper validation.

## Instrument Master And Options

Angel index option orders require the NFO trading symbol and token from the instrument master. This project now supports a cached master file:

```powershell
python -m nse_agentic_trader.app --mode paper --symbol NIFTY --refresh-instruments
```

Then paper trade a mapped option contract:

```powershell
python -m nse_agentic_trader.app --mode paper --symbol NIFTY --option-strike 22500 --option-expiry 2026-06-04
```

If the cache is missing or the contract cannot be found, the app falls back to the original index-symbol paper sample instead of attempting any live action.

Paper option orders now require a reference price, enforce lot-size multiples when a contract is mapped, apply configurable slippage, track positions, and can simulate conservative stop/target exits from candle highs and lows.

## Safety Rules

- Daily max loss stops new trades.
- Max trades per day stops overtrading.
- Max quantity caps position size.
- Live orders require an explicit environment flag.
- Every signal, rejection, and fill is journaled.
- Option selling remains paper-only until explicit future approval and additional risk systems exist.
