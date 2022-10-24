import io
import json
import typing
from . import traversers, manual_testing, logic, human


def extract_indicator_key_from_indicator(indicator):
    return human.pretty_indicator(indicator['fn'], indicator['val'], indicator['window-days'])


def express_comparator_in_python(comparator_string: str) -> str:
    if comparator_string == logic.ComposerComparison.LTE:
        return "<="
    if comparator_string == logic.ComposerComparison.LT:
        return "<"
    if comparator_string == logic.ComposerComparison.GTE:
        return ">="
    if comparator_string == logic.ComposerComparison.GT:
        return ">"
    if comparator_string == logic.ComposerComparison.EQ:
        return "=="
    print(f"UNEXPECTED comparator {comparator_string}")
    return comparator_string


def get_code_to_reference_indicator(indicator) -> str:
    if indicator['fn'] == logic.ComposerIndicatorFunction.CURRENT_PRICE:
        return f"closes['{indicator['val']}'][day]"
    else:
        key = extract_indicator_key_from_indicator(indicator)
        return f"indicators['{key}'][day]"


def express_condition(child_node) -> str:
    lhs_indicator = traversers.extract_lhs_indicator(
        child_node)
    lhs_expression = get_code_to_reference_indicator(
        lhs_indicator)

    rhs_indicator = traversers.extract_rhs_indicator(
        child_node)
    if not rhs_indicator:
        rhs_expression = f"{child_node[':rhs-val']}"
    else:
        rhs_expression = get_code_to_reference_indicator(
            rhs_indicator)

    return f"{lhs_expression} {express_comparator_in_python(child_node[':comparator'])} {rhs_expression}"


def print_python_logic(node, parent_node_branch_state: typing.Optional[logic.NodeBranchState] = None, indent: int = 0, file=None):
    """
    Traverses tree and prints out python code for populating allocations dataframe.
    """
    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = logic.NodeBranchState(1, [], "")
    parent_node_branch_state = typing.cast(
        logic.NodeBranchState, parent_node_branch_state)

    current_node_branch_state = logic.advance_branch_state(
        parent_node_branch_state, node)

    def indented_print(msg: str, indent_offset=0):
        print(("  " * (indent + indent_offset)) + msg, file=file)

    # :wt-cash-equally and :wt-cash-specified is handled by logic.advance_branch_state logic for us
    # TODO: Weight inverse by volatility (similar approach to :filter)
    # TODO: weight by market cap dynamically, how to get data?

    if logic.is_if_node(node):
        for i, child_node in enumerate(logic.get_node_children(node)):
            if i == 0:
                indented_print(f"if {express_condition(child_node)}:")
            elif logic.is_conditional_node(child_node):
                indented_print(f"elif {express_condition(child_node)}:")
            else:
                indented_print("else:")
            print_python_logic(
                child_node, parent_node_branch_state=current_node_branch_state, indent=indent+1, file=file)
        return
    elif logic.is_asset_node(node):
        indented_print(
            f"branch_tracker['{current_node_branch_state.branch_path_ids[-1]}'][day] = 1")
        indented_print(
            f"allocations['{logic.get_ticker_of_asset_node(node)}'][day] = {current_node_branch_state.weight}")
    elif logic.is_group_node(node):
        indented_print(f"# {node[':name']}")
    elif logic.is_filter_node(node):
        indented_print(
            f"branch_tracker['{current_node_branch_state.branch_path_ids[-1]}'][day] = 1")

        indented_print(f"for _sort_value, ticker in sorted([")
        for filter_indicator in traversers.extract_filter_indicators(node):
            fmt = extract_indicator_key_from_indicator(filter_indicator)
            indented_print(
                f"(indicators['{fmt}'][day], '{filter_indicator['val']}'),", indent_offset=1)
        indented_print(
            f"], reverse={node[':select-fn'] == ':top'})[{int(node[':select-n'])}:]:  # {node[':select-fn']} {int(node[':select-n'])}")
        indented_print(
            # The "/int(node[':select-n'])" logic is already applied in current_node_branch_state.weight
            f"allocations[ticker][day] = {current_node_branch_state.weight}", indent_offset=1)

        return

    for child_node in logic.get_node_children(node):
        print_python_logic(
            child_node, parent_node_branch_state=current_node_branch_state, indent=indent, file=file)


def convert_to_vectorbt(root_node) -> str:
    output = io.StringIO()
    _convert_to_vectorbt(root_node, file=output)
    text = output.getvalue()
    output.close()
    return text


def _convert_to_vectorbt(root_node, file=None):
    def write(*msgs):
        print(*msgs, file=file)

    all_tickers = traversers.collect_referenced_assets(root_node)
    allocateable_tickers = traversers.collect_allocateable_assets(root_node)
    indicators = traversers.collect_indicators(root_node)

    write(f"""
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
        write(
            f"closes['{ticker}'] = get_close_data('{ticker}', apply_warmup_period(start, {warmup_period_trading_days}), end)")
    write()

    write(f"""
#
# Precompute indicators
#


def precompute_indicator(close_series: pd.Series, indicator: str, window_days: int):
    if indicator == ':cumulative-return':
        raise NotImplementedError()
    elif indicator == ':moving-average-price':
        return close_series.rolling(window_days).mean()
    elif indicator == ':relative-strength-index':
        return ta.rsi(close_series)
    else:
        raise NotImplementedError("Have not implemented indicator " + indicator)

indicators = pd.DataFrame(index=closes.index)
""")
    for indicator in traversers.collect_indicators(root_node):
        if indicator['fn'] == logic.ComposerIndicatorFunction.CURRENT_PRICE:
            # nothing to precompute; just reference `closes`
            continue

        write(
            f"indicators['{extract_indicator_key_from_indicator(indicator)}'] = precompute_indicator(closes['{indicator['val']}'], '{indicator['fn']}', {indicator['window-days']})")
    write()

    branches_by_path = traversers.collect_branches(root_node)
    branches_by_leaf_node_id = {
        key.split("/")[-1]: value for key, value in branches_by_path.items()}
    write(f"""
#
# Algorithm Logic and instrumentation
#
allocations = pd.DataFrame(columns={repr(sorted(list(allocateable_tickers)))})

# Track branch usage based on :id of "leaf" condition (closest :if-child up the tree to that leaf node)
branch_tracker = pd.DataFrame(columns={repr(sorted(branches_by_leaf_node_id.keys()))})
branch_explainer_text_by_id = {json.dumps(branches_by_leaf_node_id, sort_keys=True, indent=2)}

# TODO: iterate by day, see how the vectorbtpro guys did it
for day in indicators.index:
    """)

    print_python_logic(root_node, indent=1, file=file)

    write("""
allocations.fillna(0, inplace=True)

# TODO: specify rebalance criteria (not available from root node...)
# TODO: pass to vectorbt
    """)


def main():
    path = 'inputs/tqqq_long_term.edn'
    path = 'inputs/betaballer-modified.edn'
    # path = 'inputs/simple.edn'
    root_node = manual_testing.get_root_node_from_path(path)

    print(convert_to_vectorbt(root_node))
