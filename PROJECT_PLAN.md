# Project Plan

## Goal

Build an agentic AI professional trader assistant for NSE index intraday trading using Angel One SmartAPI.

The system must support these strategy families as first-class modules:

- Scalping or momentum.
- Breakout.
- Option buying.
- Option selling.
- Trend following.
- Mean reversion.
- VWAP pullback.
- Trend continuation.
- Failed breakout / reversal.
- Avoid-trade filters for choppy markets, low volume, news/spike candles, and late entries.

Every strategy family must produce structured trade ideas with instrument, direction, entry, stop loss, target, confidence, invalidation condition, expected holding time, and reason. The AI layer reviews and challenges those ideas; it does not invent uncontrolled orders.

## Phase 1: Safe Local Prototype

- Use paper trading only.
- Implement deterministic strategy examples behind a common strategy interface.
- Add journal logging.
- Add risk manager and kill-switch rules.
- Keep AI as a reviewer/explainer.
- Start with option buying and breakout/momentum examples because the downside is naturally capped to premium paid.

## Phase 2: Angel SmartAPI Market Data

- Add SmartAPI login.
- Download and cache Angel instrument master. `nse_agentic_trader.instruments` now supports a local JSON cache and safe refresh path.
- Map NIFTY/BANKNIFTY option symbols to tokens. First pass supports `OPTIDX` lookup by underlying, strike, expiry, and CE/PE.
- Add websocket feed for live LTP/candles.
- Add a contract validation command that prints token, lot size, tick size, and expiry before a strategy can use it.

## Phase 3: Strategy Research

- Add backtesting using historical 1-minute data.
- Test opening-range breakout, VWAP pullback, trend continuation, scalping/momentum, option buying, option selling, and mean reversion.
- Track win rate, expectancy, drawdown, max adverse excursion, slippage.
- Replace the current sample option premium estimator with recorded/streamed option LTP candles for paper trading.
- Model realistic intraday costs: brokerage, exchange fees, STT, GST, stamp duty, and bid/ask spread.
- Keep option selling disabled for live trading until margin checks, defined-risk spreads, and emergency exits are implemented.
- Maintain separate metrics by strategy family, index, weekday, expiry distance, time of day, and volatility regime.

## Strategy Family Requirements

### Scalping Or Momentum

- Purpose: capture fast intraday moves in NIFTY/BANKNIFTY options.
- Inputs: 1-minute or faster candles, LTP, volume, VWAP, opening range, momentum strength, spread filter.
- Default instrument: ATM or slightly ITM option buying.
- Required controls: tight stop loss, cooldown after loss, max trades per session, no trading during illiquid/spread-widening periods.

### Breakout

- Purpose: trade clean breaks from opening range, prior high/low, VWAP bands, or consolidation zones.
- Inputs: range high/low, candle close confirmation, volume expansion, trend filter.
- Default instrument: index option buying.
- Required controls: reject late entries, reject false-break risk when candle body is weak, mandatory stop below/above breakout structure.

### VWAP Pullback

- Purpose: enter after price pulls back toward VWAP while trend remains intact.
- Inputs: VWAP, trend slope, reclaim/rejection candle, volume, spread filter.
- Default instrument: ATM or slightly ITM option buying.
- Required controls: reject flat VWAP, reject low volume, stop beyond VWAP/pullback extreme.

### Option Buying

- Purpose: directional defined-risk trades using CE/PE contracts.
- Inputs: underlying signal, option LTP, strike selection, expiry, liquidity, spread, implied volatility context when available.
- Default state: enabled for paper trading.
- Required controls: premium-at-risk cap, stop loss required, target or trailing exit, avoid far OTM illiquid contracts.

### Option Selling

- Purpose: premium capture using short options or defined-risk spreads.
- Inputs: margin availability, volatility, support/resistance, option chain, Greeks when available, expiry risk.
- Default state: research and paper only; live disabled by policy until additional controls exist.
- Required controls: margin check, max loss model, hedge/defined-risk structure preference, emergency exit, no naked live selling without explicit future approval.

### Trend Following

- Purpose: stay with sustained intraday directional moves.
- Inputs: higher-timeframe trend, moving averages, VWAP slope, market structure, trailing stop.
- Default instrument: option buying or futures/index proxy in paper.
- Required controls: avoid chop, trail stops, reduce size after extended move, exit near end of day.

### Trend Continuation

- Purpose: enter a formed trend after a shallow pause or continuation trigger.
- Inputs: moving-average alignment, slope, pullback depth, continuation candle.
- Default instrument: option buying.
- Required controls: avoid extended entries, use trailing stop, reject late-day entries.

### Mean Reversion

- Purpose: fade stretched moves back toward VWAP or range mean when market conditions support it.
- Inputs: distance from VWAP, RSI/oscillator, volatility bands, support/resistance, rejection candles.
- Default instrument: option buying in the reversal direction for capped risk.
- Required controls: only trade in non-trending regime, hard stop beyond extreme, reject against strong trend days.

### Failed Breakout / Reversal

- Purpose: fade failed breaks when price returns back inside a reference range.
- Inputs: opening range, prior high/low, failed close, rejection candle, volume behavior.
- Default instrument: option buying in the reversal direction.
- Required controls: stop beyond failed breakout extreme, avoid news-spike candles, reject repeated whipsaw.

### Avoid-Trade Filters

- Purpose: block low-quality environments before the reviewer/risk/order path.
- Filters: choppy market, low volume, news/spike candle, late entry.
- Behavior: blocked trade ideas are journaled with filter reasons and no order is placed.

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
   - `instruments validate` CLI is in place for NIFTY/BANKNIFTY contracts.
   - Cache validation reports file age, contract count, token, lot size, tick size, and expiry.
   - Add tests for weekly/monthly expiry parsing as Angel formats evolve.
2. Improve paper trading:
   - CSV candle replay and guarded Angel historical candle provider are in place.
   - Full candle-session paper replay is in place with entry count, exits, and realized P&L summary.
   - Feed real option LTP bars into option strategy execution instead of estimating premiums from index spot.
   - Simulate stop/target exits conservatively when both hit inside the same candle.
   - Estimated transaction costs and gross/net realized P&L reporting are in place.
   - Add unrealized P&L reporting for open positions.
3. Build the strategy framework:
   - Common strategy interface and strategy registry are in place.
   - CLI selection is in place for scalping, breakout, VWAP pullback, option buying, option selling, trend following, trend continuation, mean reversion, and failed breakout/reversal starter modules.
   - Avoid-trade filters are in place for choppy, low-volume, news/spike, and late-entry blocks.
   - Journal tags are in place; per-strategy paper metrics still need aggregation.
4. Strengthen risk:
   - Explicit kill switch state is persisted to disk.
   - Enforce lot-size-aware quantity sizing before broker submission.
   - Add symbol-level exposure caps for NIFTY and BANKNIFTY.
   - Add stricter rules for option selling: paper-only, margin-aware, and defined-risk first.
   - Add confirmation workflow before resetting a live kill switch.
5. Build assistant workflow:
   - Make the reviewer return structured approval, objections, and checklist items.
   - Journal summary command is in place for decision/order review.
   - Add a daily pre-market checklist and richer post-market AI narrative summary.
6. Live readiness gates:
   - Add dry-run Angel order payload validation.
   - Add manual approval prompts.
   - Add one-lot-only live pilot mode after long paper validation.

## Open-Source Repos To Study

- Angel One SmartAPI Python: https://github.com/angel-one/smartapi-python
- TradingAgents: https://github.com/TauricResearch/TradingAgents
- FinRobot: https://github.com/AI4Finance-Foundation/FinRobot
- FinRL-Trading: https://github.com/AI4Finance-Foundation/FinRL-Trading
- OpenAlice: https://github.com/TraderAlice/OpenAlice
