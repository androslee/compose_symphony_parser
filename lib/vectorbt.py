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
    key = extract_indicator_key_from_indicator(indicator)
    return f"indicators.at[row, '{key}']"


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


def print_python_logic(node, parent_node_branch_state: typing.Optional[logic.NodeBranchState] = None, indent: int = 0, indent_size: int = 4, file=None):
    """
    Traverses tree and prints out python code for populating allocations dataframe.
    """
    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = logic.build_node_branch_state_from_root_node(
            node)
    parent_node_branch_state = typing.cast(
        logic.NodeBranchState, parent_node_branch_state)

    current_node_branch_state = logic.advance_branch_state(
        parent_node_branch_state, node)

    def indented_print(msg: str, indent_offset=0):
        print((" " * indent_size * (indent + indent_offset)) + msg, file=file)

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
                child_node, parent_node_branch_state=current_node_branch_state, indent=indent+1, indent_size=indent_size, file=file)
        return
    elif logic.is_asset_node(node):
        indented_print(
            f"branch_tracker.at[row, '{current_node_branch_state.branch_path_ids[-1]}'] = 1")
        indented_print(
            f"allocations.at[row, '{logic.get_ticker_of_asset_node(node)}'] += {current_node_branch_state.weight}")
    elif logic.is_group_node(node):
        indented_print(f"# {node[':name']}")
    elif logic.is_filter_node(node):
        indented_print(
            f"branch_tracker.at[row, '{current_node_branch_state.branch_path_ids[-1]}'] = 1")

        indented_print(f"entries = [")
        for filter_indicator in traversers.extract_filter_indicators(node):
            fmt = extract_indicator_key_from_indicator(filter_indicator)
            indented_print(
                f"(indicators.at[row, '{fmt}'], '{filter_indicator['val']}'),", indent_offset=1)
        indented_print(f"]")

        indented_print(
            f"selected_entries = sorted(entries, reverse={node[':select-fn'] == ':top'})[:{int(node[':select-n'])}]")
        indented_print(f"for _sort_value, ticker in selected_entries:")
        # use weight of first child (will be same across all children)
        weight = logic.advance_branch_state(
            current_node_branch_state, logic.get_node_children(node)[0]).weight
        indented_print(
            f"allocations.at[row, ticker] += {weight}", indent_offset=1)

        # Debugging
        # indented_print(
        #     f"print(entries, '{node[':select-fn']} {node[':select-n']}', selected_entries)")

        return
    elif logic.is_weight_inverse_volatility_node(node):
        indented_print(
            f"branch_tracker.at[row, '{current_node_branch_state.branch_path_ids[-1]}'] = 1")
        indented_print(f"entries = [")
        for indicator in traversers.extract_inverse_volatility_indicators(node):
            fmt = extract_indicator_key_from_indicator(indicator)
            indented_print(
                f"(1/indicators.at[row, '{fmt}'], '{indicator['val']}'),", indent_offset=1)
        indented_print(f"]")
        indented_print(
            f"overall_inverse_volatility = sum(t[0] for t in entries)")
        indented_print(f"for inverse_volatility, ticker in entries:")
        # use weight of first child (will be same across all children)
        weight = logic.advance_branch_state(
            current_node_branch_state, logic.get_node_children(node)[0]).weight
        indented_print(
            f"allocations.at[row, ticker] += {weight} * (inverse_volatility / overall_inverse_volatility)", indent_offset=1)

        return

    for child_node in logic.get_node_children(node):
        print_python_logic(
            child_node, parent_node_branch_state=current_node_branch_state, indent=indent, indent_size=indent_size, file=file)


def convert_to_vectorbt(root_node) -> str:
    assert not traversers.collect_nodes_of_type(
        ":wt-marketcap", root_node), "Market cap weighting is not supported."

    output = io.StringIO()
    _convert_to_vectorbt(root_node, file=output)
    text = output.getvalue()
    output.close()
    return text


def _convert_to_vectorbt(root_node, file=None):
    def write(*msgs):
        print(*msgs, file=file)

    write(f"""

def build_allocations_matrix(closes):
    indicators = pd.DataFrame(index=closes.index)
""")
    for indicator in traversers.collect_indicators(root_node):
        write(
            f"    indicators['{extract_indicator_key_from_indicator(indicator)}'] = precompute_indicator(closes['{indicator['val']}'], '{indicator['fn']}', {indicator['window-days']})")
    write("""
    # If any indicator is not available, we cannot compute that day
    # (assumes all na's stop at some point and then are continuously available into the future, no skips)
    indicators.dropna(axis=0, inplace=True)
    """)

    branches_by_path = traversers.collect_branches(root_node)
    branches_by_leaf_node_id = {
        key.split("/")[-1]: value for key, value in branches_by_path.items()}
    write(f"""
    #
    # Algorithm Logic and instrumentation
    #
    allocations = pd.DataFrame(index=indicators.index, columns=closes.columns).fillna(0.0)

    # Track branch usage based on :id of "leaf" condition (closest :if-child up the tree to that leaf node)
    branch_tracker = pd.DataFrame(index=indicators.index, columns={repr(sorted(branches_by_leaf_node_id.keys()))}).fillna(0)

    for row in indicators.index:
    """)

    print_python_logic(root_node, indent=2, indent_size=4, file=file)

    write("""
    return allocations, branch_tracker
    """)


def main():
    path = 'inputs/tqqq_long_term.edn'
    path = 'inputs/betaballer-modified.edn'
    # path = 'inputs/simple.edn'
    root_node = manual_testing.get_root_node_from_path(path)

    print(convert_to_vectorbt(root_node))
