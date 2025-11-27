import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict
from typing import Any, Dict, List


from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

from private.core_logic.config import ALPACA_KEY, ALPACA_SECRET


class TradeFetcher:

    def __init__(self, *, alpaca_key, alpaca_secret):
        self.trading_client = TradingClient(
            alpaca_key,
            alpaca_secret,
            paper=True,
        )

    def _get_closed_orders(self, after: datetime, until: datetime, limit: int):
        """
        Fetch raw CLOSED orders (filled + canceled + expired), newest → oldest.
        We DO NOT filter to filled here.
        """
        req = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            limit=limit,
            after=after,
            until=until,
            nested=False,
        )
        return self.trading_client.get_orders(filter=req)


    def get_trades_bypass_limit(
        self,
        after: datetime,
        until: datetime,
        limit_per_request: int = 500,):
        """
        Paginate backwards in time over CLOSED orders,
        but only store FILLED ones.
        Critical fix: pagination is based on the oldest CLOSED order,
        NOT the oldest FILLED order (avoids skipping trades).
        """

        trades = []
        after_ = after
        until_ = until
        eps = timedelta(microseconds=1)

        while True:
            print(f"Fetching trades from {after_} to {until_}")
            orders = self._get_closed_orders(after=after_, until=until_, limit=limit_per_request)
            print(f"Fetched {len(orders)} closed orders")

            if not orders:
                print("No more orders, stopping")
                break

            fills = [o for o in orders if str(o.status).lower().endswith("filled")]
            print(f"  → {len(fills)} filled")
            trades.extend(fills)

            # use the OLDEST CLOSED order for pagination
            oldest_closed = orders[-1].submitted_at
            until_ = oldest_closed - eps

            if len(orders) < limit_per_request:
                print("Last page reached")
                break

        print(f"Total filled trades collected: {len(trades)}")
        return trades



    def pair_round_trips_from_orders(self, filled_orders: List[Any]) -> List[Dict[str, Any]]:
        """
        Pair up buy/sell orders for the same symbol into simple round trips.

        filled_orders: list of alpaca.trading.models.Order (status = filled)

        Assumptions:
        - You basically do: BUY x -> SELL x -> flat per symbol.
        - No scaling in/out, no partial exits, no overlapping trades.
        """
        # normalise orders into a simple structure
        norm_rows = []

        for o in filled_orders:
            symbol = getattr(o, "symbol", None)
            side_enum = getattr(o, "side", None)
            filled_qty = getattr(o, "filled_qty", None) or getattr(o, "qty", None)
            filled_price = getattr(o, "filled_avg_price", None) or getattr(o, "limit_price", None)
            filled_at = getattr(o, "filled_at", None) or getattr(o, "updated_at", None)
            order_id = getattr(o, "id", None)

            if not (symbol and side_enum and filled_qty and filled_price and filled_at):
                continue

            side = getattr(side_enum, "value", str(side_enum)).lower()

            try:
                qty = float(filled_qty)
                price = float(filled_price)
            except (TypeError, ValueError):
                continue

            if qty <= 0:
                continue

            if not isinstance(filled_at, datetime):
                # just in case, but alpaca already gives datetime
                filled_at = datetime.fromisoformat(str(filled_at))

            norm_rows.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": price,
                    "time": filled_at,
                    "order_id": order_id,
                    "raw": o,
                }
            )

        # group by symbol
        by_symbol: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in norm_rows:
            by_symbol[row["symbol"]].append(row)

        round_trips: List[Dict[str, Any]] = []

        for symbol, rows in by_symbol.items():
            rows.sort(key=lambda r: r["time"])  # oldest first
            i = 0
            n = len(rows)

            while i + 1 < n:
                buy = rows[i]
                sell = rows[i + 1]

                # require buy -> sell sequence
                if buy["side"] != "buy" or sell["side"] != "sell":
                    i += 1
                    continue

                # require exact qty match
                if buy["qty"] != sell["qty"]:
                    i += 1
                    continue

                qty = buy["qty"]
                buy_price = buy["price"]
                sell_price = sell["price"]

                pnl_amount = (sell_price - buy_price) * qty
                pnl_percentage = (sell_price - buy_price) / buy_price

                round_trips.append(
                    {
                        "symbol": symbol,
                        "qty": qty,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "buy_time": buy["time"],
                        "sell_time": sell["time"],
                        "pnl_amount": pnl_amount,
                        "pnl_percentage": pnl_percentage,
                        "buy_order_id": buy["order_id"],
                        "sell_order_id": sell["order_id"],
                        #"buy_raw": buy["raw"],
                        #"sell_raw": sell["raw"],
                    }
                )

                i += 2  # move past this pair

        return round_trips
