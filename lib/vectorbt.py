from . import traversers


# TODO: still in progress
def convert_to_vectorbt(root_node) -> str:

    # Fetch data needed
    all_tickers = traversers.collect_referenced_assets(root_node)
    print(f"start, end = datetime.date(2020, 1, 1), datetime.date(2020, 6, 1)")
    print(f"all_tickers = {repr(all_tickers)}")
    print(f"for ticker in all_tickers:")
    print(f"    closes[ticker] = get_close_data(ticker, start, end)")

    # Precompute all indicators needed
    print(traversers.collect_indicators(root_node))

    return ""
