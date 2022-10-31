import copy
import typing

from . import logic, human, symphony_object


def collect_allocateable_assets(node) -> typing.Set[str]:
    s = set()
    if logic.is_asset_node(node):
        s.add(logic.get_ticker_of_asset_node(node))
        return s

    for child in logic.get_node_children(node):
        s.update(collect_allocateable_assets(child))
    return s


def collect_if_referenced_assets(node) -> typing.Set[str]:
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


def collect_referenced_assets(node) -> typing.Set[str]:
    s = set()
    s.update(collect_if_referenced_assets(node))
    s.update(collect_allocateable_assets(node))
    return s


def extract_lhs_indicator(node):
    return {
        "fn": node[":lhs-fn"],
        "val": node[":lhs-val"],
        "window-days": int(node.get(":lhs-window-days", 0)),
    }


def extract_rhs_indicator(node) -> typing.Optional[dict]:
    if node.get(':rhs-fixed-value?', False):
        return
    return {
        "fn": node[":rhs-fn"],
        "val": node[":rhs-val"],
        "window-days": int(node.get(":rhs-window-days", 0)),
    }


def extract_filter_indicators(node) -> typing.List[dict]:
    indicators = []
    for ticker in [logic.get_ticker_of_asset_node(child) for child in logic.get_node_children(node)]:
        indicators.append({
            "fn": node[":sort-by-fn"],
            "val": ticker,
            "window-days": int(node[":sort-by-window-days"]),
        })
    return indicators


def extract_inverse_volatility_indicators(node) -> typing.List[dict]:
    indicators = []
    for ticker in [logic.get_ticker_of_asset_node(child) for child in logic.get_node_children(node)]:
        indicators.append({
            "fn": logic.ComposerIndicatorFunction.STANDARD_DEVIATION_RETURNS,
            "val": ticker,
            "window-days": int(node[":window-days"]),
        })
    return indicators


def collect_indicators(node, parent_node_branch_state=None) -> typing.List[dict]:
    """
    Collects indicators referenced
    """

    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = logic.build_node_branch_state_from_root_node(
            node)
    parent_node_branch_state = typing.cast(
        logic.NodeBranchState, parent_node_branch_state)

    current_node_branch_state = logic.advance_branch_state(
        parent_node_branch_state, node)

    indicators = []
    if logic.is_conditional_node(node):
        indicator = extract_lhs_indicator(node)
        indicator.update({
            "source": ":if-child lhs",
            "branch_path_ids": copy.copy(current_node_branch_state.branch_path_ids),
            "weight": current_node_branch_state.weight,
        })
        indicators.append(indicator)

        indicator = extract_rhs_indicator(node)
        if indicator:
            indicator.update({
                "source": ":if-child rhs",
                "branch_path_ids": copy.copy(current_node_branch_state.branch_path_ids),
                "weight": current_node_branch_state.weight,
            })
            indicators.append(indicator)

    if logic.is_filter_node(node):
        for indicator in extract_filter_indicators(node):
            indicator.update({
                "source": ":filter sort-by",
                "branch_path_ids": copy.copy(current_node_branch_state.branch_path_ids),
                "weight": current_node_branch_state.weight,
            })
            indicators.append(indicator)

    if logic.is_weight_inverse_volatility_node(node):
        for indicator in extract_inverse_volatility_indicators(node):
            indicator.update({
                "source": ":wt-inverse-vol",
                "branch_path_ids": copy.copy(current_node_branch_state.branch_path_ids),
                "weight": current_node_branch_state.weight,
            })
            indicators.append(indicator)

    for child in logic.get_node_children(node):
        indicators.extend(collect_indicators(
            child, parent_node_branch_state=current_node_branch_state))
    return indicators


def collect_conditions(node) -> typing.List[dict]:
    """
    Collects :if-child conditions used
    """

    conditions = []
    if logic.is_conditional_node(node):
        copy_node = copy.deepcopy(node)
        del copy_node[":children"]
        del copy_node[":step"]
        copy_node["pretty_text"] = human.pretty_condition(node)
        conditions.append(copy_node)

    for child in logic.get_node_children(node):
        conditions.extend(collect_conditions(child))
    return conditions


def collect_terminal_branch_paths(node, parent_node_branch_state: typing.Optional[logic.NodeBranchState] = None) -> typing.Set[str]:
    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = logic.build_node_branch_state_from_root_node(
            node)
    parent_node_branch_state = typing.cast(
        logic.NodeBranchState, parent_node_branch_state)

    current_node_branch_state = logic.advance_branch_state(
        parent_node_branch_state, node)

    branch_paths = set()
    if logic.is_asset_node(node):
        branch_paths.add("/".join(current_node_branch_state.branch_path_ids))

    for child in logic.get_node_children(node):
        branch_paths.update(collect_terminal_branch_paths(
            child, parent_node_branch_state=current_node_branch_state))

    return branch_paths


def collect_condition_strings_by_id(node, parent_node=None, parent_node_branch_state: typing.Optional[logic.NodeBranchState] = None) -> typing.Mapping[str, str]:
    """
    Collects all conditional logics of each path leading out of an :if and :if-child block (including 'else' logic and earlier 'if's)
    """

    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = logic.build_node_branch_state_from_root_node(
            node)
    parent_node_branch_state = typing.cast(
        logic.NodeBranchState, parent_node_branch_state)

    current_node_branch_state = logic.advance_branch_state(
        parent_node_branch_state, node)

    condition_strings_by_id = {}
    if logic.is_if_child_node(node):
        siblings = logic.get_node_children(parent_node)
        current_index, _ = next(filter(
            lambda index_sibling_node_tuple: index_sibling_node_tuple[1][":id"] == node[":id"], enumerate(siblings)))
        older_siblings = siblings[:current_index]

        condition_string_sibling_aware = ""
        if older_siblings:
            condition_string_sibling_aware += " and ".join(
                ["(not " + human.pretty_condition(s) + ")" for s in older_siblings])
        if logic.is_conditional_node(node) and older_siblings:
            condition_string_sibling_aware += " and "
        if logic.is_conditional_node(node):
            condition_string_sibling_aware += human.pretty_condition(node)

        condition_strings_by_id[node[":id"]] = condition_string_sibling_aware

    for child in logic.get_node_children(node):
        child_condition_strings_by_id = collect_condition_strings_by_id(
            child, parent_node=node, parent_node_branch_state=current_node_branch_state)
        condition_strings_by_id.update(child_condition_strings_by_id)
    return condition_strings_by_id


def collect_branches(root_node) -> typing.Mapping[str, str]:
    """
    Returns human-readable expressions of all the logic involved to get to an :asset node.
    """
    branch_paths = collect_terminal_branch_paths(root_node)
    condition_strings_by_id = collect_condition_strings_by_id(root_node)

    branches_by_path = {}
    for branch_path in branch_paths:
        conditional_ids = branch_path.split("/")
        condition_strings = [condition_strings_by_id.get(condition_id, "[always]")
                             for condition_id in conditional_ids]
        branches_by_path[branch_path] = " AND ".join(condition_strings)
    return branches_by_path


# TODO: collect parameters we might optimize
# - periods
# - if :rhs-fixed-value, then :rhs-val
# - stuff in :filter


def collect_nodes_of_type(step: str, node: dict) -> typing.List[dict]:
    s = []
    if node[":step"] == step:
        s.append(node)
    for child_node in logic.get_node_children(node):
        s.extend(collect_nodes_of_type(step, child_node))
    return s


def main():
    import pprint

    symphony_id = "RspMV6gSM7tX3x6yEseZ"
    symphony = symphony_object.get_symphony(symphony_id)
    root_node = symphony_object.extract_root_node_from_symphony_response(
        symphony)

    assert not collect_nodes_of_type(
        ":wt-inverse-vol", root_node), "Inverse volatility weighting is not supported."
    assert not collect_nodes_of_type(
        ":wt-marketcap", root_node), "Market cap weighting is not supported."
