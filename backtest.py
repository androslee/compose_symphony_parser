import json
import os
import pickle
import typing
import yfinance
import pandas as pd
import pandas_ta
import requests
import edn_format
import vectorbt as vbt
import quantstats

from lib import edn_syntax, logic, traversers, transpilers


import datetime
from zoneinfo import ZoneInfo


UTC_TIMEZONE = ZoneInfo("UTC")


def epoch_days_to_date(days: int) -> datetime.date:
    # if your offset is negative, this will fix the off-by-one error
    # if your offset is positive, you'll never know this problem even exists
    return datetime.datetime.fromtimestamp(days * 24 * 60 * 60, tz=UTC_TIMEZONE).date()


def date_to_epoch_days(day: datetime.date) -> int:
    return int(datetime.datetime.combine(day, datetime.time(
        0, 0), tzinfo=UTC_TIMEZONE).timestamp() / 60 / 60 / 24)


assert epoch_days_to_date(19289) == datetime.date(2022, 10, 24)


def get_backtest_data(tickers: typing.Set[str], use_simulated_data: bool = False) -> pd.DataFrame:
    # TODO: make sure all data is adjusted to the same date
    # (if writing to disc on Jan 1 but today is Dec 1, that's 11mo where dividends and splits may have invalided everything)

    # TODO: if current time is during market hours, then exclude today (yfinance inconsistent about including it)

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
                    
    if use_simulated_data:
        simulated_data = pd.read_csv("data/simulated_data.csv", index_col=0, parse_dates=True)
        reconstructed_columns = []
        for ticker in main_dataframe.columns:
            if ticker in simulated_data.columns:
                combined_series = main_dataframe[ticker].combine_first(simulated_data[ticker])
                reconstructed_columns.append(combined_series)
            else:
                reconstructed_columns.append(main_dataframe[ticker])

        main_simulated_dataframe = pd.concat(reconstructed_columns, axis=1).astype("float64")
        
        return typing.cast(pd.DataFrame, main_simulated_dataframe)
    
    return typing.cast(pd.DataFrame, main_dataframe)


def precompute_indicator(close_series: pd.Series, indicator: str, window_days: int):
    close = close_series.dropna()
    if indicator == logic.ComposerIndicatorFunction.CUMULATIVE_RETURN:
        # because comparisons will be to whole numbers
        return close.pct_change(window_days) * 100
    elif indicator == logic.ComposerIndicatorFunction.MOVING_AVERAGE_PRICE:
        return pandas_ta.sma(close, window_days)
    elif indicator == logic.ComposerIndicatorFunction.RSI:
        return pandas_ta.rsi(close, window_days)
    elif indicator == logic.ComposerIndicatorFunction.EMA_PRICE:
        return pandas_ta.ema(close, window_days)
    elif indicator == logic.ComposerIndicatorFunction.CURRENT_PRICE:
        return close_series
    elif indicator == logic.ComposerIndicatorFunction.STANDARD_DEVIATION_PRICE:
        return pandas_ta.stdev(close, window_days)
    elif indicator == logic.ComposerIndicatorFunction.STANDARD_DEVIATION_RETURNS:
        return pandas_ta.stdev(close.pct_change() * 100, window_days)
    elif indicator == logic.ComposerIndicatorFunction.MAX_DRAWDOWN:
        # this seems pretty close
        maxes = close.rolling(window_days, min_periods=1).max()
        downdraws = (close/maxes) - 1.0
        return downdraws.rolling(window_days, min_periods=1).min() * -100
    elif indicator == logic.ComposerIndicatorFunction.MOVING_AVERAGE_RETURNS:
        return close.pct_change().rolling(window_days).mean() * 100
    else:
        raise NotImplementedError(
            "Have not implemented indicator " + indicator)


def get_symphony(symphony_id: str) -> dict:

    # caching
    if not os.path.exists("data"):
        os.mkdir("data")
    path = f"data/symphony-{symphony_id}.json"
    if os.path.exists(path):
        return json.load(open(path, 'r'))

    composerConfig = {
        "projectId": "leverheads-278521",
        "databaseName": "(default)"
    }
    print(f"Fetching symphony {symphony_id} from Composer")
    response = requests.get(
        f'https://firestore.googleapis.com/v1/projects/{composerConfig["projectId"]}/databases/{composerConfig["databaseName"]}/documents/symphony/{symphony_id}')
    response.raise_for_status()

    response_json = response.json()

    json.dump(response_json, open(path, 'w'))

    return response_json


def extract_root_node_from_symphony_response(response: dict) -> dict:
    return typing.cast(dict, edn_syntax.convert_edn_to_pythonic(
        edn_format.loads(response['fields']['latest_version_edn']['stringValue'])))


def get_composer_backtest_results(symphony_id: str, start_date: datetime.date) -> dict:
    epoch_days = date_to_epoch_days(start_date)
    utc_today = datetime.datetime.now().astimezone(UTC_TIMEZONE).date()

    path = f'data/backtest-result-{symphony_id}-{epoch_days}-{date_to_epoch_days(utc_today)}.pickle'
    if os.path.exists(path):
        return pickle.load(open(path, 'rb'))

    payload = "{:uid nil, :start-date-in-epoch-days START_DATE_EPOCH_DAYS, :capital 10000, :apply-taf-fee? true, :symphony-benchmarks [], :slippage-percent 0.0005, :apply-reg-fee? true, :symphony \"SYMPHONY_ID_GOES_HERE\", :ticker-benchmarks [{:color \"#F6609F\", :id \"SPY\", :type :ticker, :checked? true, :ticker \"SPY\"}]}"
    payload = payload.replace("SYMPHONY_ID_GOES_HERE", symphony_id)
    payload = payload.replace("START_DATE_EPOCH_DAYS", str(epoch_days))

    print(
        f"Fetching backtest results for {symphony_id} from {start_date} to {utc_today}...")
    response = requests.post(
        "https://backtest.composer.trade/v2/backtest",
        json=payload)
    response.raise_for_status()
    backtest_result = edn_syntax.convert_edn_to_pythonic(
        edn_format.loads(response.text))

    pickle.dump(backtest_result, open(path, 'wb'))

    return typing.cast(dict, backtest_result)


def extract_allocations_from_composer_backtest_result(backtest_result: dict) -> pd.DataFrame:
    composer_allocations = pd.DataFrame(
        backtest_result[':tdvm-weights']).fillna(0).round(4)
    composer_allocations.index = pd.DatetimeIndex(
        [epoch_days_to_date(i) for i in composer_allocations.index])
    composer_allocations.sort_index(inplace=True)
    return composer_allocations.round(4)


def main():
    symphony_id = "ENIv7HRFOYK5q7CW91NX"
    use_simulated_data = False

    symphony = get_symphony(symphony_id)
    symphony_name = symphony['fields']['name']['stringValue']
    root_node = extract_root_node_from_symphony_response(symphony)

    tickers = traversers.collect_referenced_assets(root_node)
    allocateable_tickers = traversers.collect_allocateable_assets(root_node)
    branches_by_path = traversers.collect_branches(root_node)
    branches_by_leaf_node_id = {
        key.split("/")[-1]: value for key, value in branches_by_path.items()}

    #
    # Get Data
    #
    benchmark_ticker = "SPY"
    closes = get_backtest_data(tickers.union([benchmark_ticker]), use_simulated_data=use_simulated_data)

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

    allocations_possible_start = closes.dropna().index.min().date()
    # truncate until allocations possible (branch_tracker is not truncated)
    allocations = allocations[allocations.index.date >
                              allocations_possible_start]

    #
    # Allocation / Branch Reporting
    #
    logic_start = branch_tracker.index.min().date()

    backtest_days_count = len(allocations.index)
    backtest_start = allocations.dropna().index.min().date()
    backtest_end = allocations.index.max().date()

    print(
        f"Logic can execute from {logic_start} ({len(branch_tracker.index)})")
    print(f"Allocations can start {allocations_possible_start}")
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
    print()
    print()

    #
    # Compare to Composer's allocations
    #
    # TODO: why is Composer giving 500 errors?
    # backtest_result = get_composer_backtest_results(
    #     symphony_id, backtest_start)
    # composer_allocations = extract_allocations_from_composer_backtest_result(
    #     backtest_result)

    # print(composer_allocations)
    # print(allocations)

    #
    # VectorBT
    #
    closes_aligned = closes[closes.index.date >=
                            backtest_start].reindex_like(allocations)

    portfolio = vbt.Portfolio.from_orders(
        close=closes_aligned,
        size=allocations,
        size_type="targetpercent",
        group_by=True,
        cash_sharing=True,
        call_seq="auto",
        # TODO: rebalancing
        freq='D',
        # TODO: work out Alpaca fees
        fees=0,
    )
    returns = portfolio.asset_value().pct_change().dropna()

    #
    # Quantstats Report
    #
    filepath = "data/output.html"
    quantstats.reports.html(
        returns, closes[benchmark_ticker].pct_change().dropna(), title=f"{symphony_name}", output=filepath, download_filename=filepath)
