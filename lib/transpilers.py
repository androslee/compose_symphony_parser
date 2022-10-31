import abc
import typing

import pandas as pd
import pandas_ta

from . import human, vectorbt, logic, traversers


class Transpiler():
    @abc.abstractstaticmethod
    def convert_to_string(cls, root_node: dict) -> str:
        raise NotImplementedError()


class HumanTextTranspiler():
    @staticmethod
    def convert_to_string(root_node: dict) -> str:
        return human.convert_to_pretty_format(root_node)


#
# TODO: include this inside vectorbt output
#
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


class VectorBTTranspiler():
    @staticmethod
    def convert_to_string(root_node: dict) -> str:
        return vectorbt.convert_to_vectorbt(root_node)

    @staticmethod
    def execute(root_node: dict, closes: pd.DataFrame) -> typing.Tuple[pd.DataFrame, pd.DataFrame]:
        code = VectorBTTranspiler.convert_to_string(root_node)
        locs = {}
        exec(code, None, locs)
        build_allocations_matrix = locs['build_allocations_matrix']

        allocations, branch_tracker = build_allocations_matrix(closes)

        allocateable_tickers = traversers.collect_allocateable_assets(
            root_node)

        # remove tickers that were never intended for allocation
        for reference_only_ticker in [c for c in allocations.columns if c not in allocateable_tickers]:
            del allocations[reference_only_ticker]

        allocations_possible_start = closes[list(
            allocateable_tickers)].dropna().index.min().date()
        # truncate until allocations possible (branch_tracker is not truncated)
        allocations = allocations[allocations.index.date >=
                                  allocations_possible_start]

        return allocations, branch_tracker


def main():
    from . import symphony_object, get_backtest_data

    symphony_id = "KvA0KYc57MQSyykdWcFs"
    symphony = symphony_object.get_symphony(symphony_id)
    root_node = symphony_object.extract_root_node_from_symphony_response(
        symphony)

    print(HumanTextTranspiler.convert_to_string(root_node))
    print(VectorBTTranspiler.convert_to_string(root_node))

    tickers = traversers.collect_referenced_assets(root_node)

    closes = get_backtest_data.get_backtest_data(tickers)

    #
    # Execute logic
    #
    allocations, branch_tracker = VectorBTTranspiler.execute(
        root_node, closes)

    backtest_start = allocations.dropna().index.min().date()

    allocations_aligned = allocations[allocations.index.date >= backtest_start]
    branch_tracker_aligned = branch_tracker[branch_tracker.index.date >= backtest_start]

    assert len(allocations_aligned) == len(branch_tracker_aligned)

    print(allocations_aligned[(
        allocations_aligned.sum(axis=1) - 1).abs() > 0.0001])
    branches_by_failed_allocation_days = branch_tracker_aligned[(
        allocations_aligned.sum(axis=1) - 1).abs() > 0.0001].sum(axis=0)
    branches_with_failed_allocation_days = branches_by_failed_allocation_days[
        branches_by_failed_allocation_days != 0].index.values

    for branch_id in branches_with_failed_allocation_days:
        print(f"  -> id={branch_id}")
        print(allocations_aligned[branch_tracker_aligned[branch_id] == 1])
