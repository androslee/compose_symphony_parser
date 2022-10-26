import os
import typing
import yfinance
import pandas as pd
import pandas_ta

from lib import manual_testing, traversers, transpilers


def get_backtest_data(tickers: typing.Set[str]) -> pd.DataFrame:
    # TODO: make sure all data is adjusted to the same date
    # (if writing to disc on Jan 1 but today is Dec 1, that's 11mo where dividends and splits may have invalided everything)

    # TODO: if current time is during market hours, then exclude today (yfinance inconsistent about including it)

    # TODO: use LETF synthesized data where possible

    tickers_to_fetch = []
    for ticker in tickers:
        if not os.path.exists(f"data/adj-close_{ticker}.csv"):
            tickers_to_fetch.append(ticker)

    if tickers_to_fetch:
        data = yfinance.download(tickers_to_fetch)

        # yfinance behaves different depending on number of tickers
        if len(tickers_to_fetch) > 1:
            for ticker in tickers_to_fetch:
                data['Adj Close'][ticker].dropna().sort_index().to_csv(
                    f"data/adj-close_{ticker}.csv")
        else:
            ticker = tickers_to_fetch[0]
            d = pd.DataFrame(data['Adj Close'])
            d = d.rename(columns={"Adj Close": ticker})
            d.to_csv(
                f"data/adj-close_{ticker}.csv")

    main_dataframe = None
    for ticker in tickers:
        data = pd.read_csv(
            f"data/adj-close_{ticker}.csv", index_col="Date", parse_dates=True)
        data = data.sort_index()

        if main_dataframe is None:
            main_dataframe = data
        else:
            main_dataframe = pd.concat([main_dataframe, data], axis=1)
    return typing.cast(pd.DataFrame, main_dataframe)


def precompute_indicator(close_series: pd.Series, indicator: str, window_days: int):
    close = close_series.dropna()
    if indicator == ':cumulative-return':
        return pandas_ta.percent_return(close, length=window_days, cumulative=True)
    elif indicator == ':moving-average-price':
        return pandas_ta.sma(close, window_days)
    elif indicator == ':relative-strength-index':
        return pandas_ta.rsi(close, window_days)
    # STANDARD_DEVIATION_PRICE = ":todo"  # pandas_ta.stdev
    # STANDARD_DEVIATION_RETURNS = ":todo"  # (guessing) pandas_ta.stdev(closes.pct_change(), window_days)
    # MAX_DRAWDOWN = ":todo"  # pandas_ta.max_drawdown
    # MOVING_AVERAGE_RETURNS = ":todo"  # pandas_ta.percent_return(length=5)
    # EMA_PRICE = ":todo" # pandas_ta.ema

    else:
        raise NotImplementedError(
            "Have not implemented indicator " + indicator)


def main():
    root_node = manual_testing.get_root_node_from_path(
        'inputs/tqqq_long_term.edn')

    tickers = traversers.collect_referenced_assets(root_node)
    allocateable_tickers = traversers.collect_allocateable_assets(root_node)
    branches_by_path = traversers.collect_branches(root_node)
    branches_by_leaf_node_id = {
        key.split("/")[-1]: value for key, value in branches_by_path.items()}

    #
    # Get Data
    #
    closes = get_backtest_data(tickers)

    #
    # Execute Logic
    #
    code = transpilers.VectorBTTranspiler.convert_to_string(root_node)
    print("=" * 80)
    print(code)
    print("=" * 80)
    locs = {}
    exec(code, None, locs)
    build_allocations_matrix = locs['build_allocations_matrix']

    allocations, branch_tracker = build_allocations_matrix(closes)

    # remove tickers that were never intended for allocation
    for reference_only_ticker in [c for c in allocations.columns if c not in allocateable_tickers]:
        del allocations[reference_only_ticker]

    #
    # Reporting
    #
    backtest_days_count = len(branch_tracker)
    backtest_start, backtest_end = branch_tracker.index.min(), branch_tracker.index.max()

    print(f"Start: {backtest_start}")
    print(f"End: {backtest_end} ({backtest_days_count} trading days)")
    print()

    # Any days without full allocation?
    print("Checking for days that are not 100% allocated...")
    # Branches involved in days where allocations fail to sum to 1
    if allocations.index[allocations.sum(axis=1) != 1].values.any():
        print("WARNING: some day's allocation failed to sum to 100%.")
        print("  (this may be parser's fault, or an unexpected feature in Composer)")
        branches_by_failed_allocation_days = branch_tracker[allocations.sum(
            axis=1) != 1].sum(axis=0)
        branches_with_failed_allocation_days = branches_by_failed_allocation_days[
            branches_by_failed_allocation_days != 0].index.values

        for branch_id in branches_with_failed_allocation_days:
            print(f"  -> id={branch_id} {branches_by_leaf_node_id[branch_id]}")
    else:
        print("All days are 100% allocated.")
    print()

    print("Allocations by ticker (allocation% * days%)")
    ticker_allocation_weights = allocations.mean(
        axis=0).sort_values(ascending=False)
    for ticker in ticker_allocation_weights.index:
        print(f"  {ticker:<5} {ticker_allocation_weights[ticker]:>5.1%}")
    print()
    print()

    print("Days each branch was activated (all branches may total > 100%)")
    branch_enablement = branch_tracker.mean(
        axis=0).sort_values(ascending=False)
    for branch_id in branch_enablement.index:
        print(f"{branch_enablement[branch_id]:>5.1%} ({branch_enablement[branch_id] * backtest_days_count:>4.0f} of {backtest_days_count})",
              branches_by_leaf_node_id[branch_id])
