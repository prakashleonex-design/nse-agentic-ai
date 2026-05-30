# Project Plan

## Goal

Build an agentic AI trading assistant for NSE index intraday trading using Angel One SmartAPI.

## Phase 1: Safe Local Prototype

- Use paper trading only.
- Implement deterministic strategy examples.
- Add journal logging.
- Add risk manager and kill-switch rules.
- Keep AI as a reviewer/explainer.

## Phase 2: Angel SmartAPI Market Data

- Add SmartAPI login.
- Download and cache Angel instrument master. `nse_agentic_trader.instruments` now supports a local JSON cache and safe refresh path.
- Map NIFTY/BANKNIFTY option symbols to tokens. First pass supports `OPTIDX` lookup by underlying, strike, expiry, and CE/PE.
- Add websocket feed for live LTP/candles.
- Add a contract validation command that prints token, lot size, tick size, and expiry before a strategy can use it.

## Phase 3: Strategy Research

- Add backtesting using historical 1-minute data.
- Test opening-range breakout, VWAP pullback, and trend continuation.
- Track win rate, expectancy, drawdown, max adverse excursion, slippage.
- Replace the current sample option premium estimator with recorded/streamed option LTP candles for paper trading.
- Model realistic intraday costs: brokerage, exchange fees, STT, GST, stamp duty, and bid/ask spread.

## Phase 4: Agent Workflow

- Add market context agent.
- Add risk review agent.
- Add trade journal summarizer.
- Add manual approval before live orders.
- Require agent objections to be journaled even when a deterministic risk check approves a trade.

## Phase 5: Controlled Live Trading

- Start with one lot or minimum quantity.
- Use hard max loss and max order count.
- Send Telegram/WhatsApp alerts.
- Stop trading automatically after error bursts or API disconnects.
- Keep live placement blocked unless `TRADING_MODE=live`, `ALLOW_LIVE_ORDERS=true`, token mapping succeeds, and manual approval is recorded.

## Immediate Development Roadmap

1. Finish instrument workflows:
   - Add `instruments validate` CLI for NIFTY/BANKNIFTY contracts.
   - Cache refresh should report file age and contract count.
   - Add tests for weekly/monthly expiry parsing as Angel formats evolve.
2. Improve paper trading:
   - Feed real option LTP bars instead of estimating premiums from index spot.
   - Simulate stop/target exits conservatively when both hit inside the same candle.
   - Add transaction costs and realized/unrealized P&L reporting.
3. Strengthen risk:
   - Add explicit kill switch state persisted to disk.
   - Enforce lot-size-aware quantity sizing before broker submission.
   - Add symbol-level exposure caps for NIFTY and BANKNIFTY.
4. Build assistant workflow:
   - Make the reviewer return structured approval, objections, and checklist items.
   - Add a daily pre-market checklist and post-market journal summary.
5. Live readiness gates:
   - Add dry-run Angel order payload validation.
   - Add manual approval prompts.
   - Add one-lot-only live pilot mode after long paper validation.

## Open-Source Repos To Study

- Angel One SmartAPI Python: https://github.com/angel-one/smartapi-python
- TradingAgents: https://github.com/TauricResearch/TradingAgents
- FinRobot: https://github.com/AI4Finance-Foundation/FinRobot
- FinRL-Trading: https://github.com/AI4Finance-Foundation/FinRL-Trading
- OpenAlice: https://github.com/TraderAlice/OpenAlice
