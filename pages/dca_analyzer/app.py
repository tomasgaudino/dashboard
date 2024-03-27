import os
import plotly.graph_objs as go
import streamlit as st
import math
from utils.os_utils import get_databases
from utils.database_manager import DatabaseManager
from utils.graphs import PerformanceGraphs
from data_viz.performance.performance_charts import PerformanceCharts
from data_viz.performance.performance_candles import PerformanceCandles
from data_viz.tracers import PerformancePlotlyTracer
import data_viz.utils as utils
from utils.st_utils import initialize_st_page, download_csv_button, db_error_message


initialize_st_page(title="DCA Performance", icon="🚀")

if st.session_state.get("upload_folder") is None:
    st.session_state["upload_folder"] = "data"

# Start content here
intervals = {
    "1m": 60,
    "3m": 60 * 3,
    "5m": 60 * 5,
    "15m": 60 * 15,
    "30m": 60 * 30,
    "1h": 60 * 60,
    "6h": 60 * 60 * 6,
    "1d": 60 * 60 * 24,
}

# Data source section
st.subheader("🔫 Data source")
col1, col2 = st.columns(2)
with col1:
    with st.expander("I want to choose a different source folder"):
        upload_folder = st.text_input("Enter the folder path where the databases are stored", value=st.session_state["upload_folder"])
        if st.button("Save"):
            st.session_state["upload_folder"] = upload_folder
with col2:
    # Upload database
    with st.expander("⬆️ Upload"):
        uploaded_db = st.file_uploader("Select a Hummingbot SQLite Database", type=["sqlite", "db"])
        if uploaded_db is not None:
            file_contents = uploaded_db.read()
            with open(os.path.join(st.session_state["upload_folder"], uploaded_db.name), "wb") as f:
                f.write(file_contents)
            st.success("File uploaded and saved successfully!")
            selected_db = DatabaseManager(uploaded_db.name)

# Find and select existing databases
dbs = get_databases(root_folder=st.session_state["upload_folder"])
if dbs is not None:
    bot_source = st.selectbox("Choose your database source:", dbs.keys())
    db_names = [x for x in dbs[bot_source]]
    selected_db_name = st.selectbox("Select a database to start:", db_names)
    selected_db = DatabaseManager(db_name=dbs[bot_source][selected_db_name])
else:
    st.warning("Ups! No databases were founded. Start uploading one")
    selected_db = None
    st.stop()

# Load strategy data
strategy_data = selected_db.get_strategy_data()
main_performance_charts = PerformanceGraphs(strategy_data)
performance_charts = PerformanceCharts(strategy_data)

# Strategy summary section
st.divider()
st.subheader("📝 Strategy summary")
if not main_performance_charts.has_summary_table:
    db_error_message(db=selected_db,
                     error_message="Inaccesible summary table. Please try uploading a new database.")
    st.stop()
else:
    main_tab, chart_tab = st.tabs(["Main", "Chart"])
    with chart_tab:
        st.plotly_chart(performance_charts.realized_pnl_over_trading_pair_fig, use_container_width=True)
    with main_tab:
        selection = (main_performance_charts.strategy_summary_table_v2() if strategy_data.executors is not None
                     else main_performance_charts.strategy_summary_table_v1())
        if selection is None:
            st.info("💡 Choose a trading pair and start analyzing!")
            st.stop()
        elif len(selection) > 1:
            st.warning("This version doesn't support multiple selections. Please try selecting only one.")
            st.stop()
        else:
            selected_exchange = selection["Exchange"].values[0]
            selected_trading_pair = selection["Trading Pair"].values[0]
            selected_version = selection["Strategy Version"].values[0]
            single_market_strategy_data = strategy_data.get_single_market_strategy_data(selected_exchange, selected_trading_pair)



# Explore Trading Pair section
st.divider()
st.subheader("🔍 Explore Controllers")

if any("Error" in status for status in [selected_db.status["trade_fill"], selected_db.status["orders"]]):
    db_error_message(db=selected_db,
                     error_message="Database error. Check the status of your database.")
    st.stop()

# TODO: Add controllers summary here
controller_configs = []
selected_controller = main_performance_charts.controllers_summary_table()
if selected_controller is None:
    st.info("💡 Choose a controller and start analyzing!")
    st.stop()
elif len(selected_controller) > 1:
    st.warning("This version doesn't support multiple selections. Please try selecting only one.")
    st.stop()
else:
    selected_controller_id = selected_controller["Controller ID"].values[0]
    selected_controller_data = strategy_data.executors[(strategy_data.executors["controller_id"] == selected_controller_id) &
                                                       (strategy_data.executors["net_pnl_quote"] != 0)].sort_values("datetime")

# Performance section
st.divider()
st.subheader("📊 Performance")
tracer = PerformancePlotlyTracer()
# CLose types fig
close_types_fig = go.Figure()
close_types_df = selected_controller_data.groupby("close_type").size().reset_index(name="count")
close_types_fig.add_trace(go.Pie(labels=close_types_df["close_type"],
                                 values=close_types_df["count"],
                                 hole=0.5,
                                 title="Close Types"))

sides_fig = go.Figure()
sides_df = selected_controller_data.groupby("side").size().reset_index(name="count")
sides_fig.add_trace(go.Pie(labels=sides_df["side"].apply(lambda x: "Buy" if x == 1 else "Sell"),
                           values=sides_df["count"],
                           hole=0.5,
                           title="Sides"))

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(close_types_fig, use_container_width=True)
with col2:
    st.plotly_chart(sides_fig, use_container_width=True)


st.subheader("💱 Market activity")
if "Error" in selected_db.status["market_data"] or single_market_strategy_data.market_data.empty:
    st.warning("Market data is not available so the candles graph is not going to be rendered."
               "Make sure that you are using the latest version of Hummingbot and market data recorder activated.")
else:
    col1, col2 = st.columns(2)
    with col1:
        interval = st.selectbox("Candles Interval:", intervals.keys(), index=2)
    with col2:
        rows_per_page = st.number_input("Candles per Page", value=5000, min_value=1, max_value=5000)

    # Add pagination
    total_rows = len(single_market_strategy_data.get_market_data_resampled(interval=f"{intervals[interval]}S"))
    total_pages = math.ceil(total_rows / rows_per_page)
    if total_pages > 1:
        selected_page = st.select_slider("Select page", list(range(total_pages)), total_pages - 1, key="page_slider")
    else:
        selected_page = 0
    start_idx = selected_page * rows_per_page
    end_idx = start_idx + rows_per_page
    candles_df = single_market_strategy_data.get_market_data_resampled(interval=f"{intervals[interval]}S").iloc[start_idx:end_idx]
    start_time_page = candles_df.index.min()
    end_time_page = candles_df.index.max()

    # Get Page Filtered Strategy Data
    page_filtered_strategy_data = single_market_strategy_data.get_filtered_strategy_data(start_time_page, end_time_page)
    page_performance_charts = PerformanceGraphs(page_filtered_strategy_data)
    page_charts = PerformanceCharts(page_filtered_strategy_data)
    performance_candles = PerformanceCandles(source=page_filtered_strategy_data,
                                             executor_version=selected_version,
                                             rows=3,
                                             row_heights=[0.6, 0.2, 0.2],
                                             indicators_config=None,
                                             candles_df=candles_df,
                                             show_dca_prices=False,
                                             show_positions=True,
                                             show_buys=False,
                                             show_sells=False,
                                             show_pnl=False,
                                             show_quote_inventory_change=False,
                                             show_indicators=False,
                                             main_height=False,
                                             show_annotations=True)
    candles_figure = performance_candles.figure()

    candles_figure.add_trace(go.Scatter(x=selected_controller_data["datetime"],
                                        y=selected_controller_data["cum_net_pnl_quote"],
                                        mode="lines",
                                        fill="tozeroy",
                                        name="Cum Realized PnL (Quote)"), row=2, col=1)
    candles_figure.add_trace(go.Scatter(x=selected_controller_data["datetime"],
                                        y=selected_controller_data["cum_filled_amount_quote"],
                                        mode="lines",
                                        fill="tozeroy",
                                        name="Cum Volume (Quote)"), row=3, col=1)
    for index, rown in selected_controller_data.iterrows():
        if abs(rown["net_pnl_quote"]) > 0:
            candles_figure.add_trace(tracer.get_positions_traces(position_number=rown["id"],
                                                                 open_time=rown["datetime"],
                                                                 close_time=rown["close_datetime"],
                                                                 open_price=rown["bep"],
                                                                 close_price=rown["close_price"],
                                                                 side=rown["side"],
                                                                 close_type=rown["close_type"],
                                                                 stop_loss=rown["sl"], take_profit=rown["tp"],
                                                                 time_limit=rown["tl"],
                                                                 net_pnl_quote=rown["net_pnl_quote"]),
                                     row=1, col=1)
    candles_figure.update_yaxes(title_text="Realized PnL ($)", row=2, col=1)
    candles_figure.update_yaxes(title_text="Volume ($)", row=3, col=1)
    st.plotly_chart(candles_figure, use_container_width=True)

# Tables section
st.divider()
st.subheader("Tables")
with st.expander("💵 Trades"):
    st.write(strategy_data.trade_fill)
    download_csv_button(strategy_data.trade_fill, "trade_fill", "download-trades")
with st.expander("📩 Orders"):
    st.write(strategy_data.orders)
    download_csv_button(strategy_data.orders, "orders", "download-orders")
with st.expander("⌕ Order Status"):
    st.write(strategy_data.order_status)
    download_csv_button(strategy_data.order_status, "order_status", "download-order-status")
if not strategy_data.market_data.empty:
    with st.expander("💱 Market Data"):
        st.write(strategy_data.market_data)
        download_csv_button(strategy_data.market_data, "market_data", "download-market-data")
if strategy_data.executors is not None and not strategy_data.executors.empty:
    with st.expander("🤖 Executors"):
        st.write(strategy_data.executors)
        download_csv_button(strategy_data.executors, "executors", "download-executors")
