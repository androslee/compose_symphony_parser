import io
import typing

from . import logic, manual_testing


# TODO: how should a transpiler handle unexpected values? logging.warning? Throw an exception? Leave a TODO comment in the output?

def main():
    # path = 'inputs/inputFile.edn'
    # path = 'inputs/jamestest.edn'
    path = 'inputs/tqqq_long_term.edn'
    root_node = manual_testing.get_root_node_from_path(path)
    print(convert_to_pretty_format(root_node))


def pretty_fn(fn_string: str) -> str:
    if fn_string == logic.ComposerIndicatorFunction.RSI:
        return "RSI"
    if fn_string == logic.ComposerIndicatorFunction.CURRENT_PRICE:
        return "Close"
    if fn_string == logic.ComposerIndicatorFunction.CUMULATIVE_RETURN:
        return "CumulativeReturn"
    if fn_string == logic.ComposerIndicatorFunction.MOVING_AVERAGE_PRICE:
        return "SMA"
    if fn_string == logic.ComposerIndicatorFunction.EMA_PRICE:
        return "EMA"
    if fn_string == logic.ComposerIndicatorFunction.STANDARD_DEVIATION_PRICE:
        return "STDEV"
    if fn_string == logic.ComposerIndicatorFunction.STANDARD_DEVIATION_RETURNS:
        return "STDEVReturns"
    if fn_string == logic.ComposerIndicatorFunction.MAX_DRAWDOWN:
        return "MaxDrawdown"
    if fn_string == logic.ComposerIndicatorFunction.MOVING_AVERAGE_RETURNS:
        return "SMAReturns"
    print(f"UNEXPECTED function {fn_string}")
    return fn_string


def pretty_comparison(comparator_string: str) -> str:
    if comparator_string == logic.ComposerComparison.LTE:
        return "<="
    if comparator_string == logic.ComposerComparison.LT:
        return "<"
    if comparator_string == logic.ComposerComparison.GTE:
        return ">="
    if comparator_string == logic.ComposerComparison.GT:
        return ">"
    if comparator_string == logic.ComposerComparison.EQ:
        return "="
    print(f"UNEXPECTED comparator {comparator_string}")
    return comparator_string


def pretty_indicator(fn: str, val, window_days: typing.Optional[int]):
    if fn == logic.ComposerIndicatorFunction.CURRENT_PRICE:
        return f"{pretty_fn(fn)}({val})"
    else:
        return f"{pretty_fn(fn)}({val}, {window_days}d)"


def pretty_lhs(node) -> str:
    if type(node[":lhs-val"]) != str:
        return node[":lhs-val"]
    else:
        return pretty_indicator(node[":lhs-fn"], node[":lhs-val"], node.get(":lhs-window-days"))


def pretty_rhs(node) -> str:
    if node.get(':rhs-fixed-value?', type(node[':rhs-val']) != str):
        return node[':rhs-val']
    else:
        return pretty_indicator(node[":rhs-fn"], node[":rhs-val"], node.get(":rhs-window-days"))


def pretty_condition(node) -> str:
    return f"{pretty_lhs(node)} {pretty_comparison(node[':comparator'])} {pretty_rhs(node)}"


def pretty_selector(node) -> str:
    if node[":select-fn"] == ":bottom":
        return f"bottom {node[':select-n']}"
    elif node[":select-fn"] == ":top":
        return f"top {node[':select-n']}"
    else:
        return f"UNEXPECTED :select-fn {node[':select-fn']}"


def pretty_filter(node) -> str:
    return f"{pretty_selector(node)} by {pretty_indicator(node[':sort-by-fn'], '____', node[':sort-by-window-days'])}"


def print_children(node, depth=0, parent_node_branch_state: typing.Optional[logic.NodeBranchState] = None, file=None):
    """
    Recursively visits every child node (depth-first)
    and pretty-prints it out.
    """
    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = logic.build_node_branch_state_from_root_node(
            node)
    parent_node_branch_state = typing.cast(
        logic.NodeBranchState, parent_node_branch_state)

    current_node_branch_state = logic.advance_branch_state(
        parent_node_branch_state, node)

    def pretty_log(message: str):
        s = "  " * depth

        weight_factor = logic.extract_weight_factor(
            parent_node_branch_state, node)
        if not logic.is_weight_node(node) and weight_factor != 1:
            s += f"{weight_factor:.0%} => "

        s += message

        if logic.is_asset_node(node):
            s += f" (max: {current_node_branch_state.weight:.1%})"
        print(s, file=file)

    if logic.is_root_node(node):
        pretty_log(node[":name"])
    elif logic.is_equal_weight_node(node):
        # sometimes children will have :weight (sometimes inserted as a no-op)
        pretty_log("Weight equally:")
    elif logic.is_specified_weight_node(node):
        # children will have :weight
        # ':weight': {':num': 88, ':den': 100}, (numerator and denominator)
        pretty_log("Weight accordingly:")
    elif logic.is_weight_inverse_volatility_node(node):
        pretty_log(
            f"Weight inversely to {pretty_indicator(logic.ComposerIndicatorFunction.STANDARD_DEVIATION_RETURNS, '____', node[':window-days'])}")
    elif logic.is_if_node(node):
        pretty_log("if")
    elif logic.is_if_child_node(node):
        if not logic.is_conditional_node(node):
            pretty_log("else")
        else:
            pretty_log(f"({pretty_condition(node)})")
    elif logic.is_group_node(node):
        pretty_log(f"// {node[':name']}")
    elif logic.is_filter_node(node):
        pretty_log(pretty_filter(node))
    elif logic.is_asset_node(node):
        pretty_log(logic.get_ticker_of_asset_node(node))
    else:
        pretty_log(f"UNIMPLEMENTED: {node[':step']}")

    for child in logic.get_node_children(node):
        print_children(child, depth=depth+1,
                       parent_node_branch_state=current_node_branch_state, file=file)


def convert_to_pretty_format(root_node) -> str:
    output = io.StringIO()
    print_children(root_node, file=output)
    text = output.getvalue()
    output.close()
    return text
