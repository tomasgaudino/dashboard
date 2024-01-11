import plotly.graph_objs as go
import pandas as pd
from data_viz.dtypes import IndicatorsConfigBase
from data_viz.dtypes import PositionsVisualConfig
from datetime import datetime


class PandasTAPlotlyTracer:
    def __init__(self, candles_df: pd.DataFrame, indicators_config: IndicatorsConfigBase):
        """
        :param candles_df: candles dataframe with timestamp as index
        """
        self.candles_df = candles_df
        self.indicators_config = indicators_config

    @staticmethod
    def raise_error_if_not_enough_data(indicator_title: str):
        print(f"Not enough data to calculate {indicator_title}")

    def get_bollinger_bands_traces(self):
        config = self.indicators_config.bollinger_bands.copy()
        self.candles_df.ta.bbands(length=config.length, std=config.std, append=True)
        if len(self.candles_df) < config.length:
            self.raise_error_if_not_enough_data(config.title)
            return
        else:
            bbu_trace = go.Scatter(x=self.candles_df.index,
                                   y=self.candles_df[f'BBU_{config.length}_{config.std}'],
                                   name=f'BBU_{config.length}_{config.std}',
                                   mode='lines',
                                   line=dict(color=config.color, width=1))
            bbm_trace = go.Scatter(x=self.candles_df.index,
                                   y=self.candles_df[f'BBM_{config.length}_{config.std}'],
                                   name=f'BBM_{config.length}_{config.std}',
                                   mode='lines',
                                   line=dict(color=config.color, width=1))
            bbl_trace = go.Scatter(x=self.candles_df.index,
                                   y=self.candles_df[f'BBL_{config.length}_{config.std}'],
                                   name=f'BBL_{config.length}_{config.std}',
                                   mode='lines',
                                   line=dict(color=config.color, width=1))
            return bbu_trace, bbm_trace, bbl_trace

    def get_ema_traces(self):
        config = self.indicators_config.ema.copy()
        if len(self.candles_df) < config.length:
            self.raise_error_if_not_enough_data(config.title)
            return
        else:
            self.candles_df.ta.ema(length=config.length, append=True)
            ema_trace = go.Scatter(x=self.candles_df.index,
                                   y=self.candles_df[f'EMA_{config.length}'],
                                   name=f'EMA_{config.length}',
                                   mode='lines',
                                   line=dict(color=config.color, width=1))
            return ema_trace

    def get_macd_traces(self, fast=12, slow=26, signal=9):
        config = self.indicators_config.macd.copy()
        if len(self.candles_df) < any([config.fast, config.slow, config.signal]):
            self.raise_error_if_not_enough_data(config.title)
            return
        else:
            self.candles_df.ta.macd(fast=fast, slow=slow, signal=signal, append=True)
            macd_trace = go.Scatter(x=self.candles_df.index,
                                    y=self.candles_df[f'MACD_{fast}_{slow}_{signal}'],
                                    name=f'MACD_{fast}_{slow}_{signal}',
                                    mode='lines',
                                    line=dict(color=config.color, width=1))
            macd_signal_trace = go.Scatter(x=self.candles_df.index,
                                           y=self.candles_df[f'MACDs_{fast}_{slow}_{signal}'],
                                           name=f'MACDs_{fast}_{slow}_{signal}',
                                           mode='lines',
                                           line=dict(color=config.color, width=1))
            macd_hist_trace = go.Bar(x=self.candles_df.index,
                                     y=self.candles_df[f'MACDh_{fast}_{slow}_{signal}'],
                                     name=f'MACDh_{fast}_{slow}_{signal}',
                                     marker=dict(color=config.color))
            return macd_trace, macd_signal_trace, macd_hist_trace

    def get_rsi_traces(self, length=14):
        config = self.indicators_config.rsi.copy()
        if len(self.candles_df) < config.length:
            self.raise_error_if_not_enough_data(config.title)
            return
        else:
            self.candles_df.ta.rsi(length=length, append=True)
            rsi_trace = go.Scatter(x=self.candles_df.index,
                                   y=self.candles_df[f'RSI_{length}'],
                                   name=f'RSI_{length}',
                                   mode='lines',
                                   line=dict(color=config.color, width=1))
            return rsi_trace


class PositionsPlotlyTracer:
    def __init__(self,
                 positions_visual_config: PositionsVisualConfig = PositionsVisualConfig()):
        self.positions_visual_config = positions_visual_config

    @staticmethod
    def get_buy_traces(data: pd.DataFrame(), time_column: str, price_column: str):
        buy_trades_trace = go.Scatter(
            x=data[time_column],
            y=data[price_column],
            name="Buy Orders",
            mode="markers",
            marker=dict(
                symbol="triangle-up",
                color="green",
                size=12,
                line=dict(color="black", width=1),
                opacity=0.7,
            ),
            hoverinfo="text",
            hovertext=data[price_column].apply(lambda x: f"Buy Order: {x} <br>")
        )
        return buy_trades_trace

    @staticmethod
    def get_sell_traces(data: pd.DataFrame(), time_column: str, price_column: str):
        sell_trades_trace = go.Scatter(
            x=data[time_column],
            y=data[price_column],
            name="Sell Orders",
            mode="markers",
            marker=dict(
                symbol="triangle-down",
                color="red",
                size=12,
                line=dict(color="black", width=1),
                opacity=0.7,
            ),
            hoverinfo="text",
            hovertext=data[price_column].apply(lambda x: f"Sell Order: {x} <br>")
        )
        return sell_trades_trace

    @staticmethod
    def get_position_trace(position_number: int,
                           open_time: datetime,
                           close_time: datetime,
                           open_price: float,
                           close_price: float,
                           side: int,
                           close_type: str,
                           stop_loss: float,
                           take_profit: float,
                           time_limit: float,
                           net_pnl_quote: float):
        positions_trace = go.Scatter(name=f"Position {position_number}",
                                     x=[open_time, close_time],
                                     y=[open_price, close_price],
                                     mode="lines",
                                     line=dict(color="lightgreen" if net_pnl_quote > 0 else "red"),
                                     hoverinfo="text",
                                     hovertext=f"Position N°: {position_number} <br>"
                                               f"Open datetime: {open_time} <br>"
                                               f"Close datetime: {close_time} <br>"
                                               f"Side: {side} <br>"
                                               f"Entry price: {open_price} <br>"
                                               f"Close price: {close_price} <br>"
                                               f"Close type: {close_type} <br>"
                                               f"Stop Loss: {100 * stop_loss:.2f}% <br>"
                                               f"Take Profit: {100 * take_profit:.2f}% <br>"
                                               f"Time Limit: {time_limit} <br>",
                                     showlegend=False)
        return positions_trace