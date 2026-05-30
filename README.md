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

The newer command form is:

```powershell
python -m nse_agentic_trader.app run --mode paper --symbol NIFTY --strategy opening_range_breakout
```

Replay candles from CSV:

```powershell
python -m nse_agentic_trader.app run --mode paper --symbol NIFTY --strategy opening_range_breakout --data-source csv --csv-path .\data\nifty_1m.csv
```

CSV columns:

```text
timestamp,symbol,open,high,low,close,volume
```

Create a local sample CSV for testing the workflow:

```powershell
python -m nse_agentic_trader.app data sample-csv --path .\data\nifty_1m.csv --symbol NIFTY --bars 120
```

Validate candle data before running a strategy:

```powershell
python -m nse_agentic_trader.app data validate --data-source csv --csv-path .\data\nifty_1m.csv --symbol NIFTY --min-bars 100
```

Fetch historical candles from Angel SmartAPI after credentials are configured:

```powershell
python -m nse_agentic_trader.app run --mode paper --symbol NIFTY --strategy opening_range_breakout --data-source angel --data-exchange NFO --data-token 56978 --from-date "2026-05-30 09:15" --to-date "2026-05-30 15:30"
```

Angel candle fetches are market-data only; they do not enable live orders.

Replay a full candle set as a paper backtest/session:

```powershell
python -m nse_agentic_trader.app backtest --symbol NIFTY --strategy opening_range_breakout --data-source csv --csv-path .\data\nifty_1m.csv --max-entries 3
```

Save a Markdown backtest report:

```powershell
python -m nse_agentic_trader.app backtest --symbol NIFTY --strategy opening_range_breakout --data-source csv --csv-path .\data\nifty_1m.csv --max-entries 3 --output .\reports\backtest-nifty.md
```

Use `--no-option-mapping` to test directly on the input symbol instead of mapping index signals to option contracts.
Use `--no-filters` only for strategy mechanics tests where you intentionally want to bypass avoid-trade filters.

Backtest summaries report gross realized P&L, estimated costs, net realized P&L, winning exits, losing exits, and win rate. Paper cost estimates are controlled by:

```text
PAPER_OPTION_SLIPPAGE_BPS=8
PAPER_OPTION_MIN_SLIPPAGE=0.05
PAPER_UNDERLYING_SLIPPAGE_BPS=1
PAPER_UNDERLYING_MIN_SLIPPAGE=0
PAPER_BROKERAGE_PER_ORDER=20
PAPER_TRANSACTION_COST_BPS=6
```

Summarize the journal:

```powershell
python -m nse_agentic_trader.app report
python -m nse_agentic_trader.app report --date 2026-05-30
```

The trade reviewer records a structured verdict (`APPROVED`, `CAUTION`, or `REJECTED`), concerns, checklist items, and reward/risk into the journal.

Validate an Angel order payload without placing it:

```powershell
python -m nse_agentic_trader.app order validate --trading-symbol NIFTY02JUN2622500CE --symboltoken 56978 --exchange NFO --side BUY --quantity 65 --lot-size 65 --stop-loss 90
```

Live-mode validation additionally requires an explicit manual approval token:

```powershell
python -m nse_agentic_trader.app order validate --trading-symbol NIFTY02JUN2622500CE --symboltoken 56978 --exchange NFO --side BUY --quantity 65 --lot-size 65 --stop-loss 90 --manual-approval APPROVE
```

This command only validates and prints the payload; it does not place an order.

Run a specific strategy:

```powershell
python -m nse_agentic_trader.app --mode paper --symbol NIFTY --strategy opening_range_breakout
```

Available starter strategy names:

- `opening_range_breakout`
- `vwap_pullback`
- `scalping_momentum`
- `option_buying`
- `option_selling`
- `trend_following`
- `trend_continuation`
- `mean_reversion`
- `failed_breakout_reversal`

Avoid-trade filters run before risk/execution and can block setups for:

- Choppy market conditions.
- Low volume.
- News/spike candles.
- Late entries.

## Angel SmartAPI Setup

Create a `.env` file from `.env.example`:

```powershell
python -m nse_agentic_trader.app config init
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

`.env` entries are file contents, not PowerShell commands. Put this inside `.env`:

```text
PAPER_BROKERAGE_PER_ORDER=20
PAPER_TRANSACTION_COST_BPS=6
```

For temporary PowerShell session variables, use PowerShell syntax instead:

```powershell
$env:PAPER_BROKERAGE_PER_ORDER = "20"
$env:PAPER_TRANSACTION_COST_BPS = "6"
```

Check the effective settings with secrets masked:

```powershell
python -m nse_agentic_trader.app config show
```

Run the daily pre-market checklist:

```powershell
python -m nse_agentic_trader.app premarket
```

Use this before paper trading to confirm mode safety, live-order guard, instrument cache, risk state, journal path, and registered strategies.

Build the post-market summary:

```powershell
python -m nse_agentic_trader.app postmarket
python -m nse_agentic_trader.app postmarket --date 2026-05-30 --output .\reports\postmarket-2026-05-30.md
```

Use this after paper trading to review journal activity, risk state, strategy mix, review verdicts, and assistant notes.

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

Validate an Angel option contract before using it:

```powershell
python -m nse_agentic_trader.app instruments validate --symbol NIFTY --option-type CE --strike 22500 --expiry 2026-06-04 --refresh-instruments
```

## Risk State And Kill Switch

Risk state is persisted locally so trade count and kill-switch state survive process restarts:

```powershell
python -m nse_agentic_trader.app risk status
python -m nse_agentic_trader.app risk kill --reason "Manual stop for the day"
python -m nse_agentic_trader.app risk reset
```

`risk reset` is intended for paper/development use. A live workflow should require stronger manual confirmation before resetting a kill switch.

## Safety Rules

- Daily max loss stops new trades.
- Max trades per day stops overtrading.
- Max quantity caps position size.
- Live orders require an explicit environment flag.
- Every signal, rejection, and fill is journaled.
- Option selling remains paper-only until explicit future approval and additional risk systems exist.
- Avoid-trade filters can block otherwise valid strategy signals before order placement.
