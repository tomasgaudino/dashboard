import datetime
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class StrategyData:
    orders: pd.DataFrame
    order_status: pd.DataFrame
    trade_fill: pd.DataFrame
    market_data: pd.DataFrame = None
    executors: pd.DataFrame = None

    @property
    def controllers_summary(self):
        return self.get_controllers_summary()

    def get_controllers_summary(self):
        if self.executors is not None:
            controllers_data = self.executors[self.executors["net_pnl_quote"] != 0].copy()
            grouped_controllers = (controllers_data.groupby(["controller_id", "type"])
                                   .agg({"id": "count",
                                         "cum_net_pnl_quote": [full_series, "last"]}).reset_index())
            grouped_controllers.columns = [f"{col[0]}_{col[1]}" if len(col[1]) > 0 else col[0] for col in grouped_controllers.columns]
            controller_columns_dict = {
                "controller_id": "Controller ID",
                "type": "Type",
                "id_count": "# Positions",
                "cum_net_pnl_quote_full_series": "Realized PnL Over Time",
                "cum_net_pnl_quote_last": "Realized PnL"
            }
            grouped_controllers.rename(columns=controller_columns_dict, inplace=True)
            grouped_controllers.sort_values(["Realized PnL"], ascending=True, inplace=True)
            grouped_controllers["Explore"] = False
            grouped_controllers = grouped_controllers.reindex(columns=["Explore", "Controller ID", "Type", "# Positions",
                                                                       "Realized PnL Over Time", "Realized PnL"])
            return grouped_controllers
        else:
            return None

    @property
    def strategy_summary(self):
        return self.get_strategy_summary()

    def get_strategy_summary(self):
        grouped_trade_fill = self.get_grouped_trade_fill_data()
        if grouped_trade_fill is None:
            return None

        # Add executors info, if there is any
        if self.executors is not None:
            strategy_version = "v2"
            # Get non zero net_pnl_quote executors
            executors_data = self.executors[self.executors["net_pnl_quote"] != 0].copy()

            # Add calculated columns
            executors_data["cum_net_pnl_quote"] = executors_data["net_pnl_quote"].cumsum()

            # Group by exchange and trading pair + Final Pnl + PnL Over Time
            grouped_executors = (executors_data.groupby(["exchange", "trading_pair"])
                                 .agg(
                                    {"id": "count",
                                     "cum_net_pnl_quote": [full_series, "last"]})
                                 .reset_index())
            grouped_executors.columns = [f"{col[0]}_{col[1]}" if len(col[1]) > 0 else col[0] for col in grouped_executors.columns]

            # Merge with grouped trade fill
            strategy_summary = grouped_trade_fill.merge(grouped_executors, left_on=["market", "symbol"],
                                                        right_on=["exchange", "trading_pair"],
                                                        how="left")

            # Drop unnecesary columns
            strategy_summary.drop(columns=["exchange", "trading_pair", "net_realized_pnl_last"], inplace=True)

            # Add version column
            strategy_summary["Strategy Version"] = strategy_version

        else:
            strategy_version = "v1"
            strategy_summary = grouped_trade_fill.copy()
            strategy_summary["net_pnl_quote_full_series"] = np.nan
            strategy_summary["net_pnl_quote_last"] = np.nan
            strategy_summary["Strategy Version"] = strategy_version

        # Rename columns
        columns_dict = {"strategy": "Strategy",
                        "market": "Exchange",
                        "symbol": "Trading Pair",
                        "order_id_count": "# Trades",
                        "id_count": "# Positions",
                        "volume_sum": "Volume",
                        "net_realized_pnl_full_series": "Unrealized PnL Over Time" if strategy_version == "v2" else "Realized PnL Over Time",
                        "net_realized_pnl_last": "Unrealized PnL" if strategy_version == "v2" else "Realized PnL",
                        "cum_net_pnl_quote_full_series": "Realized PnL Over Time",
                        "cum_net_pnl_quote_last": "Realized PnL"}
        strategy_summary.rename(columns=columns_dict, inplace=True)

        # Sort by ascending Realized PnL
        strategy_summary.sort_values(["Realized PnL"], ascending=True, inplace=True)

        # Add extra columns
        strategy_summary["Explore"] = False

        # Set final order
        sorted_cols = ["Explore", "Strategy", "Strategy Version", "Exchange", "Trading Pair", "# Trades", "Volume", "# Positions",
                       "Unrealized PnL Over Time", "Realized PnL Over Time", "Realized PnL"] if strategy_version == "v2" else \
            ["Explore", "Strategy", "Strategy Version", "Exchange", "Trading Pair", "# Trades", "Volume", "Realized PnL Over Time", "Realized PnL"]
        strategy_summary = strategy_summary.reindex(columns=sorted_cols, fill_value=0)
        return strategy_summary

    def get_grouped_trade_fill_data(self):
        # Get trade fill data
        trade_fill_data = self.trade_fill.copy()
        if trade_fill_data is None:
            return None
        trade_fill_data["volume"] = trade_fill_data["amount"] * trade_fill_data["price"]
        grouped_trade_fill = trade_fill_data.groupby(["strategy", "market", "symbol"]
                                                     ).agg({"order_id": "count",
                                                            "volume": "sum",
                                                            "net_realized_pnl": [full_series,
                                                                                 "last"]}).reset_index()
        grouped_trade_fill.columns = [f"{col[0]}_{col[1]}" if len(col[1]) > 0 else col[0] for col in grouped_trade_fill.columns]
        return grouped_trade_fill

    def get_single_market_strategy_data(self, exchange: str, trading_pair: str, controller_id: str = None):
        orders = self.orders[(self.orders["market"] == exchange) & (self.orders["symbol"] == trading_pair)].copy()
        trade_fill = self.trade_fill[self.trade_fill["order_id"].isin(orders["id"])].copy()
        order_status = self.order_status[self.order_status["order_id"].isin(orders["id"])].copy()
        if self.market_data is not None:
            market_data = self.market_data[(self.market_data["exchange"] == exchange) &
                                           (self.market_data["trading_pair"] == trading_pair)].copy()
        else:
            market_data = None
        if self.executors is not None:
            if controller_id is None:
                executors = self.executors[(self.executors["exchange"] == exchange) &
                                           (self.executors["trading_pair"] == trading_pair)].copy()
            else:
                executors = self.executors[(self.executors["exchange"] == exchange) &
                                           (self.executors["trading_pair"] == trading_pair) &
                                           (self.executors["controller_id"] == controller_id)].copy()

        else:
            executors = None
        return SingleMarketStrategyData(
            exchange=exchange,
            trading_pair=trading_pair,
            orders=orders,
            order_status=order_status,
            trade_fill=trade_fill,
            market_data=market_data,
            executors=executors
        )

    @property
    def exchanges(self):
        return self.trade_fill["market"].unique()

    @property
    def trading_pairs(self):
        return self.trade_fill["symbol"].unique()

    @property
    def start_time(self):
        return self.orders["creation_timestamp"].min()

    @property
    def end_time(self):
        return self.orders["last_update_timestamp"].max()

    @property
    def duration_seconds(self):
        return (self.end_time - self.start_time).total_seconds()

    @property
    def buys(self):
        return self.trade_fill[self.trade_fill["trade_type"] == "BUY"]

    @property
    def sells(self):
        return self.trade_fill[self.trade_fill["trade_type"] == "SELL"]

    @property
    def total_buy_trades(self):
        return self.buys["amount"].count()

    @property
    def total_sell_trades(self):
        return self.sells["amount"].count()

    @property
    def total_orders(self):
        return self.total_buy_trades + self.total_sell_trades


@dataclass
class SingleMarketStrategyData:
    exchange: str
    trading_pair: str
    orders: pd.DataFrame
    order_status: pd.DataFrame
    trade_fill: pd.DataFrame
    market_data: pd.DataFrame = None
    executors: pd.DataFrame = None
    controller_id: str = None

    def get_filtered_strategy_data(self, start_date: datetime.datetime, end_date: datetime.datetime):
        orders = self.orders[
            (self.orders["creation_timestamp"] >= start_date) & (self.orders["creation_timestamp"] <= end_date)].copy()
        trade_fill = self.trade_fill[self.trade_fill["order_id"].isin(orders["id"])].copy()
        order_status = self.order_status[self.order_status["order_id"].isin(orders["id"])].copy()
        if self.market_data is not None:
            market_data = self.market_data[
                (self.market_data.index >= start_date) & (self.market_data.index <= end_date)].copy()
        else:
            market_data = None
        if self.executors is not None:
            executors = self.executors[(self.executors.datetime >= start_date) &
                                       (self.executors.datetime <= end_date) &
                                       (self.executors.controller_id == self.controller_id)].copy()
        else:
            executors = None
        return SingleMarketStrategyData(
            exchange=self.exchange,
            trading_pair=self.trading_pair,
            orders=orders,
            order_status=order_status,
            trade_fill=trade_fill,
            market_data=market_data,
            executors=executors
        )

    def get_market_data_resampled(self, interval):
        data_resampled = self.market_data.resample(interval).agg({
            "mid_price": "ohlc",
            "best_bid": "last",
            "best_ask": "last",
        })
        data_resampled.columns = data_resampled.columns.droplevel(0)
        return data_resampled

    @property
    def base_asset(self):
        return self.trading_pair.split("-")[0]

    @property
    def quote_asset(self):
        return self.trading_pair.split("-")[1]

    @property
    def start_time(self):
        return self.orders["creation_timestamp"].min()

    @property
    def end_time(self):
        return self.orders["last_update_timestamp"].max()

    @property
    def duration_seconds(self):
        return (self.end_time - self.start_time).total_seconds()

    @property
    def start_price(self):
        return self.trade_fill["price"].iat[0]

    @property
    def end_price(self):
        return self.trade_fill["price"].iat[-1]

    @property
    def buys(self):
        return self.trade_fill[self.trade_fill["trade_type"] == "BUY"]

    @property
    def sells(self):
        return self.trade_fill[self.trade_fill["trade_type"] == "SELL"]

    @property
    def total_buy_amount(self):
        return self.buys["amount"].sum()

    @property
    def total_sell_amount(self):
        return self.sells["amount"].sum()

    @property
    def total_buy_trades(self):
        return self.buys["amount"].count()

    @property
    def total_sell_trades(self):
        return self.sells["amount"].count()

    @property
    def total_orders(self):
        return self.total_buy_trades + self.total_sell_trades

    @property
    def average_buy_price(self):
        if self.total_buy_amount != 0:
            average_price = (self.buys["price"] * self.buys["amount"]).sum() / self.total_buy_amount
            return np.nan_to_num(average_price, nan=0)
        else:
            return 0

    @property
    def average_sell_price(self):
        if self.total_sell_amount != 0:
            average_price = (self.sells["price"] * self.sells["amount"]).sum() / self.total_sell_amount
            return np.nan_to_num(average_price, nan=0)
        else:
            return 0

    @property
    def price_change(self):
        return (self.end_price - self.start_price) / self.start_price

    @property
    def trade_pnl_quote(self):
        buy_volume = self.buys["amount"].sum() * self.average_buy_price
        sell_volume = self.sells["amount"].sum() * self.average_sell_price
        inventory_change_volume = self.inventory_change_base_asset * self.end_price
        return sell_volume - buy_volume + inventory_change_volume

    @property
    def cum_fees_in_quote(self):
        return self.trade_fill["trade_fee_in_quote"].sum()

    @property
    def net_pnl_quote(self):
        return self.trade_pnl_quote - self.cum_fees_in_quote

    @property
    def inventory_change_base_asset(self):
        return self.total_buy_amount - self.total_sell_amount

    @property
    def accuracy(self):
        total_wins = (self.trade_fill["net_realized_pnl"] >= 0).sum()
        total_losses = (self.trade_fill["net_realized_pnl"] < 0).sum()
        return total_wins / (total_wins + total_losses)

    @property
    def profit_factor(self):
        total_profit = self.trade_fill.loc[self.trade_fill["realized_pnl"] >= 0, "realized_pnl"].sum()
        total_loss = self.trade_fill.loc[self.trade_fill["realized_pnl"] < 0, "realized_pnl"].sum()
        return total_profit / -total_loss

    @property
    def properties_table(self):
        properties_dict = {"Base Asset": self.base_asset,
                           "Quote Asset": self.quote_asset,
                           # "Start Time": self.start_time,
                           # "End Time": self.end_time,
                           "Exchange": self.exchange,
                           "Trading pair": self.trading_pair,
                           "Duration (seconds)": self.duration_seconds,
                           "Start Price": self.start_price,
                           "End Price": self.end_price,
                           "Total Buy Amount": self.total_buy_amount,
                           "Total Sell Amount": self.total_sell_amount,
                           "Total Buy Trades": self.total_buy_trades,
                           "Total Sell Trades": self.total_sell_trades,
                           "Total Orders": self.total_orders,
                           "Average Buy Price": self.average_buy_price,
                           "Average Sell Price": self.average_sell_price,
                           "Price Change": self.price_change,
                           "Trade PnL Quote": self.trade_pnl_quote,
                           "Cum Fees in Quote": self.cum_fees_in_quote,
                           "Net PnL Quote": self.net_pnl_quote,
                           "Inventory Change (base asset)": self.inventory_change_base_asset}
        properties_table = pd.DataFrame([properties_dict]).transpose().reset_index()
        properties_table.columns = ["Metric", "Value"]
        return properties_table


def full_series(series):
    return list(series)
