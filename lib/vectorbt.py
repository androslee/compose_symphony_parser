from . import traversers, manual_testing, logic


# TODO: still in progress
def convert_to_vectorbt(root_node) -> str:
    all_tickers = traversers.collect_referenced_assets(root_node)
    allocateable_tickers = traversers.collect_allocateable_assets(root_node)
    indicators = traversers.collect_indicators(root_node)
    print(f"""
start, end = datetime.date(2020, 1, 1), datetime.date(2020, 6, 1)



#
# Fetch data
#


def get_close_data(ticker: str, fetch_start: datetime.date, fetch_end: datetime.date) -> pd.Series:
    pass  # TODO: work out data provider


def apply_warmup_period(start_date: datetime.date, trading_days: int) -> datetime.date:
    if days == 0:
        return start_date
    return start_date - datetime.timedelta(days=(trading_days * (365/252))+4)  # padded


# TODO: initialize `closes` dataframe with correct datetime index (skipping trading holidays/weekends)
closes = pd.DataFrame()
    """)
    for ticker in all_tickers:
        matching_indicators = [
            ind for ind in indicators if ind['val'] == ticker]
        warmup_period_trading_days = max(ind['window-days']
                                         for ind in matching_indicators) if matching_indicators else 0
        print(
            f"closes['{ticker}'] = get_close_data('{ticker}', apply_warmup_period(start, {warmup_period_trading_days}), end)")
    print()

    print(f"""
#
# Precompute indicators
#


def precompute_indicator(close_series: pd.Series, indicator: str, window_days: int):
    if indicator == '{logic.ComposerIndicatorFunction.CUMULATIVE_RETURN}':
        raise NotImplementedError()
    elif indicator == '{logic.ComposerIndicatorFunction.MOVING_AVERAGE_PRICE}':
        return close_series.rolling(window_days).mean()
    elif indicator == '{logic.ComposerIndicatorFunction.RSI}':
        return ta.rsi(close_series)
    else:
        raise NotImplementedError("Have not implemented indicator " + indicator)

indicators = pd.DataFrame(index=closes.index)
""")
    for indicator in traversers.collect_indicators(root_node):
        fmt = f"{indicator['val']}_{indicator['fn']}_{indicator['window-days']}"

        if indicator['fn'] == logic.ComposerIndicatorFunction.CURRENT_PRICE:
            # nothing to precompute; just reference `closes`
            continue

        print(
            f"indicators['{fmt}'] = precompute_indicator(closes['{indicator['val']}'], '{indicator['fn']}', {indicator['window-days']})")
    print()

    # Branch tracker
    # TODO: do we give each branch a uniquer id, so if we change code we don't break this?
    branches = traversers.collect_branches(root_node)
    print(f"""
#
# Algorithm Logic and instrumentation
#
allocations = pd.DataFrame(columns={repr(sorted(list(allocateable_tickers)))})
branches_triggered_by_day = pd.DataFrame(columns={repr(sorted(branches))})

# TODO: iterate by day, see how the vectorbtpro guys did it
for day in indicators.index:
    # HARDCODED - transpiler has not implemented this yet
    if closes['SPY'][day] > indicators['SPY_:moving-average-price_21'][day]:
        allocations['SPY'][day] = 0.6
        branch_tracker["ClosePrice(SPY) > SMA(SPY, 21)"][day] = 1

        if closes['BND'][day] > indicators['BND_:moving-average-price_21'][day]:
            allocations['BND'][day] = 0.4
            branch_tracker["ClosePrice(BND) > SMA(BND, 21) AND ClosePrice(SPY) > SMA(SPY, 21)"][day] = 1
        else:
            allocations['SHY'][day] = 0.4
            branch_tracker["not ClosePrice(BND) > SMA(BND, 21) AND ClosePrice(SPY) > SMA(SPY, 21)"][day] = 1
    else:
        allocations['SHY'][day] = 1
        branch_tracker["not ClosePrice(SPY) > SMA(SPY, 21)"][day] = 1
    """)
    # TODO: traverse logic tree and print out
    # - if/elif/else's
    # - asset assignments (and mark branches_triggered_by_day here) (use static weight from .logic reducer thing)
    # - :filter logic (call a function to do it?)
    # - parallel assignments on same indentation (weight-equally with 2 complex options)
    # - :group -> Python comments
    # - Also, note which branch is executed in a dataframe
    # (and put parallel assignments on same indentation)

    print("""
allocations.fillna(0, inplace=True)

# TODO: specify rebalance criteria (not available from root node...)
# TODO: pass to vectorbt
    """)
    return ""


def main():
    path = 'inputs/tqqq_long_term.edn'
    path = 'inputs/simple.edn'
    root_node = manual_testing.get_root_node_from_path(path)

    print(convert_to_vectorbt(root_node))
