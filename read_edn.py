import copy
import datetime
from enum import Enum
import typing
import edn_format
import json


def convert_edn_to_pythonic(d):
    if type(d) == edn_format.immutable_dict.ImmutableDict:
        return {convert_edn_to_pythonic(k): convert_edn_to_pythonic(v) for k, v in d.items()}
    elif type(d) == edn_format.immutable_list.ImmutableList:
        return [convert_edn_to_pythonic(v) for v in d]
    elif type(d) == edn_format.edn_lex.Keyword:
        return ":" + d.name
    else:
        return d


def main():
    # path = 'inputs/inputFile.edn'
    # path = 'inputs/jamestest.edn'
    path = 'inputs/tqqq_long_term.edn'
    try:
        # Data is wrapped with "" and has escaped all the "s, this de-escapes
        data_with_wrapping_string_removed = json.load(
            open(path, 'r'))
        root_data_immutable = edn_format.loads(
            data_with_wrapping_string_removed)
        root_data = typing.cast(
            dict, convert_edn_to_pythonic(root_data_immutable))
        root_rule = root_data[":symphony"]
    except:
        root_data_immutable = edn_format.loads(open(path, 'r').read())
        root_rule = typing.cast(
            dict, convert_edn_to_pythonic(root_data_immutable))

    print_children(root_rule)
    print()

    allocateable_assets = collect_allocateable_assets(root_rule)
    print("Possible assets to allocate toward:", allocateable_assets)
    problematic_assets = {  # TODO: look entries up (I have this in the ETF DB)
        "UGE": "Volume is too low",
        # TODO: remove this:
        "VIXY": "(Fake error for testing this code, ignore)",
    }
    for asset in allocateable_assets:
        if asset in problematic_assets:
            print("WARNING", asset, problematic_assets[asset])
    print()

    all_referenced_assets = collect_referenced_assets(root_rule)
    print("All assets referenced:", all_referenced_assets)
    latest_founded_asset = max(all_referenced_assets, key=get_founded_date)
    latest_founded_date = get_founded_date(latest_founded_asset)
    print(
        f"Earliest backtest date is {latest_founded_date} (when {latest_founded_asset} was founded)")


#
# External lookups for linting use cases
#
def get_founded_date(ticker: str) -> datetime.date:
    # TODO: look values up (I have this in the ETF DB)
    return datetime.date(2017, 7, 1)


#
# Basic tree traversers
#
def collect_allocateable_assets(node) -> set[str]:
    s = set()
    if is_asset_node(node):
        s.add(get_ticker_of_asset_node(node))
        return s

    for child in get_node_children(node):
        s.update(collect_allocateable_assets(child))
    return s


def collect_if_referenced_assets(node) -> set[str]:
    """
    Collects tickers referenced by if-conditions
    """
    s = set()
    if is_conditional_node(node):
        lhs_ticker = get_lhs_ticker(node)
        if lhs_ticker:
            s.add(lhs_ticker)
        rhs_ticker = get_rhs_ticker(node)
        if rhs_ticker:
            s.add(rhs_ticker)

    for child in get_node_children(node):
        s.update(collect_if_referenced_assets(child))
    return s


def collect_referenced_assets(node) -> set[str]:
    s = set()
    s.update(collect_if_referenced_assets(node))
    s.update(collect_allocateable_assets(node))
    return s

# TODO: collect parameters we might optimize
# - periods
# - if :rhs-fixed-value, then :rhs-val
# - stuff in :filter


#
# Traversal helpers and documentation
#
def get_node_children(node) -> list:
    return node[":children"] if ":children" in node else []


def build_basic_node_type_checker(step: str):
    def is_node_of_type(node) -> bool:
        return node[":step"] == step
    return is_node_of_type


is_root_node = build_basic_node_type_checker(":root")

is_asset_node = build_basic_node_type_checker(":asset")
# ':ticker'
# rest are ephemeral/derived from :ticker:
# ':name'
# ':has_marketcap'
# ':exchange'
# ':price'
# ':dollar_volume'

is_if_node = build_basic_node_type_checker(":if")
# All :children are definitely if-child

is_if_child_node = build_basic_node_type_checker(":if-child")
# ':is-else-condition?'
# if not an else block, see `is_conditional_node`

is_equal_weight_node = build_basic_node_type_checker(":wt-cash-equal")
# ':window-days': Optional[int] TODO: what does it mean?

is_group_node = build_basic_node_type_checker(":group")
# ':name'
# ':collapsed?'

is_filter_node = build_basic_node_type_checker(":filter")
# ':select?': should always be True... not sure why this is here.
# ':select-fn': :bottom or :top
# ':select-n': str, annoyingly. Always an int

# ':sort-by?': should always be True... not sure why this is here.
# ':sort-by-fn'
# ':sort-by-window-days': str, annoyingly

# ':weight': TODO account for this properly
# ':collapsed-specified-weight?': TODO: where is this?


def is_conditional_node(node) -> bool:
    """
    if-child and not else

    # ':lhs-fn'
    # ':lhs-window-days'
    # ':lhs-val'

    # ':comparator'

    # ':rhs-fn'
    # ':rhs-fixed-value?'
    # ':rhs-window-days'
    # ':rhs-val'
    """
    return is_if_child_node(node) and not node[":is-else-condition?"]


def get_lhs_ticker(node) -> typing.Optional[str]:
    return node[':lhs-val']


def get_rhs_ticker(node) -> typing.Optional[str]:
    # yes, rhs behaves differently than lhs.
    if not node.get(':rhs-fixed-value?', type(node[':rhs-val']) != str):
        return node[":rhs-val"]


class ComposerIndicatorFunction:
    RSI = ":relative-strength-index"
    CURRENT_PRICE = ":current-price"
    CUMULATIVE_RETURN = ":cumulative-return"
    MOVING_AVERAGE_PRICE = ":moving-average-price"
    # TODO: add more


class ComposerComparison:
    LTE = ":lte"
    LT = ":lt"
    GTE = ":gte"
    GT = ":gt"
    # TODO: add more


def get_ticker_of_asset_node(node) -> str:
    return node[':ticker']


#
# Human-readable transpiler
#

def pretty_fn(fn_string: str) -> str:
    if fn_string == ComposerIndicatorFunction.RSI:
        return "RSI"
    if fn_string == ComposerIndicatorFunction.CURRENT_PRICE:
        return "Close"
    if fn_string == ComposerIndicatorFunction.CUMULATIVE_RETURN:
        return "CumulativeReturn"
    if fn_string == ComposerIndicatorFunction.MOVING_AVERAGE_PRICE:
        # TODO: confirm this is SMA and not a different MA type like EMA
        return "SMA"
    print(f"UNEXPECTED function {fn_string}")
    return fn_string


def pretty_comparison(comparator_string: str) -> str:
    if comparator_string == ComposerComparison.LTE:
        return "<="
    if comparator_string == ComposerComparison.LT:
        return "<"
    if comparator_string == ComposerComparison.GTE:
        return ">="
    if comparator_string == ComposerComparison.GT:
        return ">"
    print(f"UNEXPECTED comparator {comparator_string}")
    return comparator_string


def debug_print_node(node):
    new_node = copy.copy(node)
    del new_node[":children"]
    del new_node[":step"]
    print(json.dumps(new_node, indent=4, sort_keys=True))


def pretty_indicator(fn: str, val, window_days: typing.Optional[int]):
    if fn == ComposerIndicatorFunction.CURRENT_PRICE:
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


def print_children(node, depth=0):
    """
    Recursively visits every child node (depth-first)
    and pretty-prints it out.
    """
    def pretty_log(message: str):
        s = "  " * depth
        if ":weight" in node:
            weight = int(node[":weight"][":num"]) / \
                int(node[":weight"][":den"])
            s += f"{weight:.0%}"
        s += " " + message
        print(s)

    if is_root_node(node):
        pretty_log(node[":name"])
    elif is_equal_weight_node(node):
        pretty_log("Weight equally:")
    elif node[":step"] == ":wt-cash-specified":
        # children will have :weight
        # ':weight': {':num': 88, ':den': 100},
        pretty_log("Weight accordingly:")
    elif is_if_node(node):
        pretty_log("if")
    elif is_if_child_node(node):
        if not is_conditional_node(node):
            pretty_log("else")
        else:
            pretty_log(pretty_condition(node))
    elif is_group_node(node):
        pretty_log(f"// {node[':name']}")
    elif is_filter_node(node):
        pretty_log(pretty_filter(node))
    elif is_asset_node(node):
        pretty_log(get_ticker_of_asset_node(node))
    else:
        pretty_log(f"UNIMPLEMENTED: {node[':step']}")

    for child in get_node_children(node):
        print_children(child, depth=depth+1)


if __name__ == "__main__":
    main()
