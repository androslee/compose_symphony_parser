import datetime
from . import traversers, manual_testing


#
# Idea: take root_node and print out all issues can check for
# - troublesome tickers / low-volume
# - tickers with little data
# - patterns/indicators we find are flawed
# - TODO: think of additional common issues we might scan for
#


def log_warnings_for_dangerous_tickers(root_node):
    allocateable_assets = traversers.collect_allocateable_assets(root_node)
    print("Possible assets to allocate toward:", allocateable_assets)
    problematic_assets = {  # TODO: look entries up (I have this in the ETF DB)
        "UGE": "Volume is too low",
        # TODO: remove this:
        "VIXY": "(Fake error for testing this code, ignore)",
    }
    for asset in allocateable_assets:
        if asset in problematic_assets:
            print("WARNING", asset, problematic_assets[asset])


def log_earliest_backtest_date(root_node):
    all_referenced_assets = traversers.collect_referenced_assets(root_node)
    print("All assets referenced:", all_referenced_assets)
    latest_founded_asset = max(all_referenced_assets, key=get_founded_date)
    latest_founded_date = get_founded_date(latest_founded_asset)
    print(
        f"Earliest backtest date is {latest_founded_date} (when {latest_founded_asset} was founded)")


def get_founded_date(ticker: str) -> datetime.date:
    print("TODO: implement actual founded_date lookup")
    return datetime.date(2012, 1, 1)


def main():
    # path = 'inputs/inputFile.edn'
    # path = 'inputs/jamestest.edn'
    path = 'inputs/tqqq_long_term.edn'
    root_node = manual_testing.get_root_node_from_path(path)

    log_warnings_for_dangerous_tickers(root_node)
    print()
    log_earliest_backtest_date(root_node)
    print()
