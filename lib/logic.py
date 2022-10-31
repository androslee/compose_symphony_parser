import copy
from dataclasses import dataclass
import typing


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
is_weight_inverse_volatility_node = build_basic_node_type_checker(
    ":wt-inverse-vol")
is_weight_marketcap_node = build_basic_node_type_checker(":wt-marketcap")


def is_weight_node(node):
    return is_equal_weight_node(node) or is_specified_weight_node(node) or is_weight_inverse_volatility_node(node) or is_weight_marketcap_node(node)


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
    CURRENT_PRICE = ":current-price"
    CUMULATIVE_RETURN = ":cumulative-return"
    STANDARD_DEVIATION_PRICE = ":standard-deviation-price"
    STANDARD_DEVIATION_RETURNS = ":standard-deviation-return"
    MAX_DRAWDOWN = ":max-drawdown"
    MOVING_AVERAGE_PRICE = ":moving-average-price"
    MOVING_AVERAGE_RETURNS = ":moving-average-return"
    EMA_PRICE = ":exponential-moving-average-price"
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
    branch_path_ids: typing.List[str]
    parent_nodes: typing.List[dict]


def build_node_branch_state_from_root_node(node) -> NodeBranchState:
    return NodeBranchState(1, [node[":id"]], [node])


def extract_weight_factor(parent_node_branch_state: NodeBranchState, node) -> float:
    # Do not care about :weight if parent type is not a specific node type (UI leaves this strewn everywhere)
    weight = 1

    parent_node_type = parent_node_branch_state.parent_nodes[-1][":step"]

    # :wt-cash-specified parent means :weight is specified on this node
    if parent_node_type == ":wt-cash-specified" and ":weight" in node:
        weight *= int(node[":weight"][":num"]) / int(node[":weight"][":den"])

    # :wt-cash-equal parent means apply equal % across all siblings of this node
    if parent_node_type == ":wt-cash-equal":
        weight /= len(get_node_children(
            parent_node_branch_state.parent_nodes[-1]))

    # :filter parent means apply equal % across :select-n of parent
    if parent_node_type == ":filter":
        weight /= int(
            parent_node_branch_state.parent_nodes[-1].get(":select-n", 1))

    # :wt-inverse-vol cannot be computed here, theoretical max is 100%
    # :wt-marketcap cannot be computed here, theoretical max is 100%

    # There are no other blocks which impact weights.

    return weight

# "reducer" signature / design pattern


def advance_branch_state(parent_node_branch_state: NodeBranchState, node) -> NodeBranchState:
    current_node_branch_state = copy.deepcopy(parent_node_branch_state)

    current_node_branch_state.parent_nodes.append(node)

    if is_if_child_node(node):
        current_node_branch_state.branch_path_ids.append(node[":id"])

    current_node_branch_state.weight *= extract_weight_factor(
        parent_node_branch_state, node)

    return current_node_branch_state
