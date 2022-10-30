import vectorbt as vbt
import quantstats

from lib import symphony_object, traversers, transpilers, get_backtest_data, symphony_backtest


def main():
    symphony_id = "2XE43Kcoqa0uLSOBuN3q"
    symphony = symphony_object.get_symphony(symphony_id)
    symphony_name = symphony['fields']['name']['stringValue']

    root_node = symphony_object.extract_root_node_from_symphony_response(
        symphony)

    tickers = traversers.collect_referenced_assets(root_node)

    #
    # Get Data
    #
    benchmark_ticker = "SPY"
    closes = get_backtest_data.get_backtest_data(
        tickers.union([benchmark_ticker]))

    #
    # Print Logic
    #
    code = transpilers.VectorBTTranspiler.convert_to_string(root_node)
    print("=" * 80)
    print(code)
    print("=" * 80)

    #
    # Execute logic
    #
    allocations, branch_tracker = transpilers.VectorBTTranspiler.execute(
        root_node, closes)

    #
    # Allocation / Branch Reporting
    #
    logic_start = branch_tracker.index.min().date()
    allocations_possible_start = allocations.index.min().date()

    backtest_start = allocations.dropna().index.min().date()
    backtest_end = allocations.index.max().date()

    print(
        f"Logic can execute from {logic_start} ({len(branch_tracker.index)})")
    print(
        f"Allocations can start {allocations_possible_start} ({len(allocations.index)})")
    print(f"Start: {backtest_start}")
    print(f"End: {backtest_end}")
    print()

    backtest_result = symphony_backtest.get_composer_backtest_results(
        symphony_id, backtest_start)
    returns = symphony_backtest.extract_returns_from_composer_backtest_result(
        backtest_result, symphony_id)

    filepath = "data/output.html"
    quantstats.reports.html(
        returns,
        # closes[benchmark_ticker].pct_change().dropna(),
        title=f"{symphony_name}", output=filepath, download_filename=filepath)

    return

    composer_allocations = symphony_backtest.extract_allocations_from_composer_backtest_result(
        backtest_result)
    print(composer_allocations)

    branches_by_path = traversers.collect_branches(root_node)
    branches_by_leaf_node_id = {
        key.split("/")[-1]: value for key, value in branches_by_path.items()}

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
    backtest_result = get_composer_backtest_results(
        symphony_id, backtest_start)
    composer_allocations = extract_allocations_from_composer_backtest_result(
        backtest_result)

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
