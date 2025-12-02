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
from private.core_logic.paths import TRADE_TRACKING_CSV_PATH, TRADE_TRACKING_CSV_PATH_PRIVATE


class TradeFetcher:

    def __init__(self, *, alpaca_key, alpaca_secret, public=False):
        self.trading_client = TradingClient(
            alpaca_key,
            alpaca_secret,
            paper=True,
        )
        self.public = public
        if public:
            self.trades_csv = TRADE_TRACKING_CSV_PATH
        else:
            self.trades_csv = TRADE_TRACKING_CSV_PATH_PRIVATE

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

                return_on_basis = pnl_amount / (buy_price * qty)

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
                        "basis": buy_price * qty,
                        "return_on_basis": return_on_basis,
                        #"buy_raw": buy["raw"],
                        #"sell_raw": sell["raw"],
                    }
                )

                i += 2  # move past this pair

        return round_trips


    def insert_trades_to_csv(self, trades):

        if self.public:
            columns = ['sell_time', 'buy_time',
                        'pnl_amount', 'pnl_percentage',
                        'basis', 'buy_order_id']
        else:
            columns = ['qty', 'buy_price', 'sell_price', 'buy_time', 'sell_time',
                        'pnl_amount', 'pnl_percentage', 'buy_order_id', 'sell_order_id',
                        'return_on_basis', 'basis']


        trades_df = pd.DataFrame(trades)[columns]

        trades_df['buy_order_id'] = trades_df['buy_order_id'].astype(str)

        try:
            print(f"Reading trades from {self.trades_csv}")
            existing_trades = pd.read_csv(self.trades_csv)
        except FileNotFoundError:
            print("file not found")
            return

        trades_df['buy_time'] = trades_df['buy_time'].dt.strftime("%Y-%m-%d")
        trades_df['sell_time'] = trades_df['sell_time'].dt.strftime("%Y-%m-%d")


        mask_new = ~trades_df["buy_order_id"].isin(existing_trades["buy_order_id"])
        trades_df_new_only = trades_df[mask_new]
        df_updated = pd.concat([existing_trades, trades_df_new_only], ignore_index=True)
        df_updated.to_csv(self.trades_csv, index=False)

        return df_updated

    
    def update_csv(self, lookback_days):

        start_date = datetime.now() - timedelta(days=lookback_days)
        end_date = datetime.now()

        trades = self.get_trades_bypass_limit(after=start_date, until=end_date, limit_per_request=500)
        trades = self.pair_round_trips_from_orders(trades)
        self.insert_trades_to_csv(trades)



