import copy
from dataclasses import dataclass
import datetime
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

# TODO: find unexpected attributes (future-proofing)
# TODO: collect all conditions from branch paths
# TODO: collect all indicators (for precomputing)


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
is_specified_weight_node = build_basic_node_type_checker(":wt-cash-specified")


def is_weight_node(node):
    return is_equal_weight_node(node) or is_specified_weight_node(node)


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
    # TODO: fill in missing symbols
    CURRENT_PRICE = ":current-price"
    CUMULATIVE_RETURN = ":cumulative-return"
    # STANDARD_DEVIATION_PRICE = ":todo"
    # STANDARD_DEVIATION_RETURNS = ":todo"
    # MAX_DRAWDOWN = ":todo"
    MOVING_AVERAGE_PRICE = ":moving-average-price"
    # MOVING_AVERAGE_RETURNS = ":todo"
    # EMA_PRICE = ":todo"
    RSI = ":relative-strength-index"


class ComposerComparison:
    LTE = ":lte"
    LT = ":lt"
    GTE = ":gte"
    GT = ":gt"
    EQ = ":eq"


def get_ticker_of_asset_node(node) -> str:
    return node[':ticker']


#
# Tree path reducer/state thinker
# - weight
# - branch path
# - parent node type (sans pass-through nodes like :group)
#
@dataclass
class NodeBranchState:
    weight: float  # do not read this on :wt-* nodes, behavior not guaranteed
    branch_path_ids: list[str]
    node_type: str


def extract_weight_factor(parent_node_branch_state: NodeBranchState, node) -> float:
    # Do not care about :weight if parent type is not a specific node type (UI leaves this strewn everywhere)
    if ":weight" in node and parent_node_branch_state.node_type in (":wt-cash-specified",):
        return int(node[":weight"][":num"]) / int(node[":weight"][":den"])
    # If equal weight, apply weight now; children will ignore any :weight instruction on them.
    elif node[":step"] == ":wt-cash-equal":
        return 1. / len(get_node_children(node))
    elif is_filter_node(node):  # equal weight all filter results
        return 1. / int(node[":select-n"])
    else:
        return 1  # no change

# "reducer" signature / design pattern


def advance_branch_state(parent_node_branch_state: NodeBranchState, node) -> NodeBranchState:
    current_node_branch_state = copy.deepcopy(parent_node_branch_state)

    if node[":step"] != ":group":
        current_node_branch_state.node_type = node[":step"]

    if is_if_child_node(node):
        current_node_branch_state.branch_path_ids.append(node[":id"])

    current_node_branch_state.weight *= extract_weight_factor(
        parent_node_branch_state, node)

    return current_node_branch_state


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
    if comparator_string == ComposerComparison.EQ:
        return "="
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


def print_children(node, depth=0, parent_node_branch_state: typing.Optional[NodeBranchState] = None):
    """
    Recursively visits every child node (depth-first)
    and pretty-prints it out.
    """
    if not parent_node_branch_state:
        # current node is :root, there is no higher node
        parent_node_branch_state = NodeBranchState(1, [], "")
    parent_node_branch_state = typing.cast(
        NodeBranchState, parent_node_branch_state)

    current_node_branch_state = advance_branch_state(
        parent_node_branch_state, node)

    def pretty_log(message: str):
        s = "  " * depth

        weight_factor = extract_weight_factor(parent_node_branch_state, node)
        if not is_weight_node(node) and weight_factor != 1:
            s += f"{weight_factor:.0%} => "

        s += message

        if is_asset_node(node):
            s += f" (max: {current_node_branch_state.weight:.1%})"
        print(s)

    if is_root_node(node):
        pretty_log(node[":name"])
    elif is_equal_weight_node(node):
        # sometimes children will have :weight (sometimes inserted as a no-op)
        pretty_log("Weight equally:")
    elif is_specified_weight_node(node):
        # children will have :weight
        # ':weight': {':num': 88, ':den': 100}, (numerator and denominator)
        pretty_log("Weight accordingly:")
    elif is_if_node(node):
        pretty_log("if")
    elif is_if_child_node(node):
        if not is_conditional_node(node):
            pretty_log("else")
        else:
            pretty_log(f"({pretty_condition(node)})")
    elif is_group_node(node):
        pretty_log(f"// {node[':name']}")
    elif is_filter_node(node):
        pretty_log(pretty_filter(node))
    elif is_asset_node(node):
        pretty_log(get_ticker_of_asset_node(node))
    else:
        pretty_log(f"UNIMPLEMENTED: {node[':step']}")

    for child in get_node_children(node):
        print_children(child, depth=depth+1,
                       parent_node_branch_state=current_node_branch_state)


if __name__ == "__main__":
    main()
