import pandas_ta as ta  # noqa: F401
import streamlit as st
from typing import Union

from utils.data_manipulation import StrategyData, SingleMarketStrategyData

BULLISH_COLOR = "rgba(97, 199, 102, 0.9)"
BEARISH_COLOR = "rgba(255, 102, 90, 0.9)"
FEE_COLOR = "rgba(51, 0, 51, 0.9)"
MIN_INTERVAL_RESOLUTION = "1m"


class PerformanceGraphs:
    BULLISH_COLOR = "rgba(97, 199, 102, 0.9)"
    BEARISH_COLOR = "rgba(255, 102, 90, 0.9)"
    FEE_COLOR = "rgba(51, 0, 51, 0.9)"

    def __init__(self, strategy_data: Union[StrategyData, SingleMarketStrategyData]):
        self.strategy_data = strategy_data

    @property
    def has_summary_table(self):
        if isinstance(self.strategy_data, StrategyData):
            return self.strategy_data.strategy_summary is not None
        else:
            return False

    def controllers_summary_table(self):
        summary = st.data_editor(self.strategy_data.controllers_summary,
                                 column_config={"Realized PnL Over Time": st.column_config.LineChartColumn("PnL Over Time",
                                                                                                  y_min=0,
                                                                                                  y_max=5000),
                                                "Explore": st.column_config.CheckboxColumn(required=True)
                                                },
                                 use_container_width=True,
                                 hide_index=True
                                 )
        selected_rows = summary[summary.Explore]
        if len(selected_rows) > 0:
            return selected_rows
        else:
            return None

    def strategy_summary_table_v2(self):
        summary = st.data_editor(self.strategy_data.strategy_summary,
                                 column_config={"Unrealized PnL Over Time": st.column_config.LineChartColumn("Unrealized PnL Over Time",
                                                                                                             y_min=0,
                                                                                                             y_max=5000),
                                                "Realized PnL Over Time": st.column_config.LineChartColumn("Realized PnL Over Time",
                                                                                                           y_min=0,
                                                                                                           y_max=5000),

                                                "Explore": st.column_config.CheckboxColumn(required=True)
                                                },
                                 use_container_width=True,
                                 hide_index=True
                                 )
        selected_rows = summary[summary.Explore]
        if len(selected_rows) > 0:
            return selected_rows
        else:
            return None

    def strategy_summary_table_v1(self):
        summary = st.data_editor(self.strategy_data.strategy_summary,
                                 column_config={"PnL Over Time": st.column_config.LineChartColumn("PnL Over Time",
                                                                                                  y_min=0,
                                                                                                  y_max=5000),
                                                "Explore": st.column_config.CheckboxColumn(required=True)
                                                },
                                 use_container_width=True,
                                 hide_index=True
                                 )
        selected_rows = summary[summary.Explore]
        if len(selected_rows) > 0:
            return selected_rows
        else:
            return None
