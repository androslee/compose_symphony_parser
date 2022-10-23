from . import logic


def collect_allocateable_assets(node) -> set[str]:
    s = set()
    if logic.is_asset_node(node):
        s.add(logic.get_ticker_of_asset_node(node))
        return s

    for child in logic.get_node_children(node):
        s.update(collect_allocateable_assets(child))
    return s


def collect_if_referenced_assets(node) -> set[str]:
    """
    Collects tickers referenced by if-conditions
    """
    s = set()
    if logic.is_conditional_node(node):
        lhs_ticker = logic.get_lhs_ticker(node)
        if lhs_ticker:
            s.add(lhs_ticker)
        rhs_ticker = logic.get_rhs_ticker(node)
        if rhs_ticker:
            s.add(rhs_ticker)

    for child in logic.get_node_children(node):
        s.update(collect_if_referenced_assets(child))
    return s


def collect_referenced_assets(node) -> set[str]:
    s = set()
    s.update(collect_if_referenced_assets(node))
    s.update(collect_allocateable_assets(node))
    return s


def collect_indicators(node) -> set[str]:
    """
    Collects tickers referenced by if-conditions
    """
    indicators = set()
    if logic.is_conditional_node(node):
        indicators.add({
            "fn": node[":lhs-fn"],
            "val": node[":lhs-val"],
            "window-days": node[":lhs-window-days"],
        })

    for child in logic.get_node_children(node):
        indicators.update(collect_indicators(child))
    return indicators

# TODO: collect parameters we might optimize
# - periods
# - if :rhs-fixed-value, then :rhs-val
# - stuff in :filter

# TODO: find unexpected attributes (future-proofing)
# TODO: collect all conditions from branch paths
# TODO: collect all indicators (for precomputing)
