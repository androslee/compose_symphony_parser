#! /usr/bin/python3
import copy
from dataclasses import dataclass
import datetime
import io
import sys
import typing
import edn_format
import json
import traceback


# copied from pull request #5 version of read_edn.py 
# from commit 43d807dea618bb45d6985e773d11f8a59088df21 


class HumanPrinter:
    
    def __init__(self):
    
        """
        These were all just globally defined before.  so i think moving them to the init makes most sense, so they run first
        """
        
    
        self.is_root_node = self.build_basic_node_type_checker(":root")

        self.is_asset_node = self.build_basic_node_type_checker(":asset")
        # ':ticker'
        # rest are ephemeral/derived from :ticker:
        # ':name'
        # ':has_marketcap'
        # ':exchange'
        # ':price'
        # ':dollar_volume'

        self.is_if_node = self.build_basic_node_type_checker(":if")
        # All :children are definitely if-child

        self.is_if_child_node = self.build_basic_node_type_checker(":if-child")
        # ':is-else-condition?'
        # if not an else block, see `is_conditional_node`

        self.is_equal_weight_node = self.build_basic_node_type_checker(":wt-cash-equal")
        self.is_specified_weight_node = self.build_basic_node_type_checker(":wt-cash-specified")






        self.is_group_node = self.build_basic_node_type_checker(":group")
        # ':name'
        # ':collapsed?'

        self.is_filter_node = self.build_basic_node_type_checker(":filter")
        # ':select?': should always be True... not sure why this is here.
        # ':select-fn': :bottom or :top
        # ':select-n': str, annoyingly. Always an int

        # ':sort-by?': should always be True... not sure why this is here.
        # ':sort-by-fn'
        # ':sort-by-window-days': str, annoyingly

    
        return


    def main(self, root_node):

        print(self.convert_to_pretty_format(root_node))
        print()

        allocateable_assets = self.collect_allocateable_assets(root_node)
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

        all_referenced_assets = self.collect_referenced_assets(root_node)
        print("All assets referenced:", all_referenced_assets)
        latest_founded_asset = max(all_referenced_assets, key=self.get_founded_date)
        latest_founded_date = self.get_founded_date(latest_founded_asset)
        print(
            f"Earliest backtest date is {latest_founded_date} (when {latest_founded_asset} was founded)")

        
    @staticmethod
    def convert_edn_to_pythonic(d):
        if type(d) == edn_format.immutable_dict.ImmutableDict:
            return {HumanPrinter.convert_edn_to_pythonic(k): HumanPrinter.convert_edn_to_pythonic(v) for k, v in d.items()}
        elif type(d) == edn_format.immutable_list.ImmutableList:
            return [HumanPrinter.convert_edn_to_pythonic(v) for v in d]
        elif type(d) == edn_format.edn_lex.Keyword:
            return ":" + d.name
        else:
            return d

    #
    # External lookups for linting use cases
    #
    def get_founded_date(self, ticker: str) -> datetime.date:
        # TODO: look values up (I have this in the ETF DB)
        return datetime.date(2017, 7, 1)


    #
    # Basic tree traversers
    #
    # leaving out the type hints because they would not work for andros
    def collect_allocateable_assets(self, node): #-> set[str]:
        s = set()
        if self.is_asset_node(node):
            s.add(self.get_ticker_of_asset_node(node))
            return s

        for child in self.get_node_children(node):
            s.update(self.collect_allocateable_assets(child))
        return s


    # leaving out the type hints because they would not work for andros
    def collect_if_referenced_assets(self, node): #-> set[str]:
        """
        Collects tickers referenced by if-conditions
        """
        s = set()
        if self.is_conditional_node(node):
            lhs_ticker = self.get_lhs_ticker(node)
            if lhs_ticker:
                s.add(lhs_ticker)
            rhs_ticker = self.get_rhs_ticker(node)
            if rhs_ticker:
                s.add(rhs_ticker)

        for child in self.get_node_children(node):
            s.update(self.collect_if_referenced_assets(child))
        return s

    # leaving out the type hints because they would not work for andros
    def collect_referenced_assets(self, node): #-> set[str]:
        s = set()
        s.update(self.collect_if_referenced_assets(node))
        s.update(self.collect_allocateable_assets(node))
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
    def get_node_children(self, node) -> list:
        return node[":children"] if ":children" in node else []


    def build_basic_node_type_checker(self, step: str):
        def is_node_of_type(node) -> bool:
            return node[":step"] == step
        return is_node_of_type



    def is_weight_node(self, node):
        return self.is_equal_weight_node(node) or self.is_specified_weight_node(node)


    def is_conditional_node(self, node) -> bool:
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
        return self.is_if_child_node(node) and not node[":is-else-condition?"]


    def get_lhs_ticker(self, node) -> typing.Optional[str]:
        return node[':lhs-val']


    def get_rhs_ticker(self, node) -> typing.Optional[str]:
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


    def get_ticker_of_asset_node(self, node) -> str:
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
        #branch_path_ids: list[str]
        # would not work for andros, so i'm just leaving it as an empty list
        branch_path_ids: list
        node_type: str


    def extract_weight_factor(self, parent_node_branch_state: NodeBranchState, node) -> float:
        # Do not care about :weight if parent type is not a specific node type (UI leaves this strewn everywhere)
        if ":weight" in node and parent_node_branch_state.node_type in (":wt-cash-specified",):
            return int(node[":weight"][":num"]) / int(node[":weight"][":den"])
        # If equal weight, apply weight now; children will ignore any :weight instruction on them.
        elif node[":step"] == ":wt-cash-equal":
            return 1. / len(self.get_node_children(node))
        elif self.is_filter_node(node):  # equal weight all filter results
            return 1. / int(node[":select-n"])
        else:
            return 1  # no change

    # "reducer" signature / design pattern


    def advance_branch_state(self, parent_node_branch_state: NodeBranchState, node) -> NodeBranchState:
        current_node_branch_state = copy.deepcopy(parent_node_branch_state)

        if node[":step"] != ":group":
            current_node_branch_state.node_type = node[":step"]

        if self.is_if_child_node(node):
            current_node_branch_state.branch_path_ids.append(node[":id"])

        current_node_branch_state.weight *= self.extract_weight_factor(
            parent_node_branch_state, node)

        return current_node_branch_state


    #
    # Human-readable transpiler
    #

    def pretty_fn(self, fn_string: str) -> str:
        if fn_string == self.ComposerIndicatorFunction.RSI:
            return "RSI"
        if fn_string == self.ComposerIndicatorFunction.CURRENT_PRICE:
            return "Close"
        if fn_string == self.ComposerIndicatorFunction.CUMULATIVE_RETURN:
            return "CumulativeReturn"
        if fn_string == self.ComposerIndicatorFunction.MOVING_AVERAGE_PRICE:
            return "SMA"
        print(f"UNEXPECTED function {fn_string}")
        return fn_string


    def pretty_comparison(self, comparator_string: str) -> str:
        if comparator_string == self.ComposerComparison.LTE:
            return "<="
        if comparator_string == self.ComposerComparison.LT:
            return "<"
        if comparator_string == self.ComposerComparison.GTE:
            return ">="
        if comparator_string == self.ComposerComparison.GT:
            return ">"
        if comparator_string == self.ComposerComparison.EQ:
            return "="
        print(f"UNEXPECTED comparator {comparator_string}")
        return comparator_string


    def debug_print_node(self, node):
        new_node = copy.copy(node)
        del new_node[":children"]
        del new_node[":step"]
        print(json.dumps(new_node, indent=4, sort_keys=True))


    def pretty_indicator(self, fn: str, val, window_days: typing.Optional[int]):
        if fn == self.ComposerIndicatorFunction.CURRENT_PRICE:
            return f"{self.pretty_fn(fn)}({val})"
        else:
            return f"{self.pretty_fn(fn)}({val}, {window_days}d)"


    def pretty_lhs(self, node) -> str:
        if type(node[":lhs-val"]) != str:
            return node[":lhs-val"]
        else:
            return self.pretty_indicator(node[":lhs-fn"], node[":lhs-val"], node.get(":lhs-window-days"))


    def pretty_rhs(self, node) -> str:
        if node.get(':rhs-fixed-value?', type(node[':rhs-val']) != str):
            return node[':rhs-val']
        else:
            return self.pretty_indicator(node[":rhs-fn"], node[":rhs-val"], node.get(":rhs-window-days"))


    def pretty_condition(self, node) -> str:
        return f"{self.pretty_lhs(node)} {self.pretty_comparison(node[':comparator'])} {self.pretty_rhs(node)}"


    def pretty_selector(self, node) -> str:
        if node[":select-fn"] == ":bottom":
            return f"bottom {node[':select-n']}"
        elif node[":select-fn"] == ":top":
            return f"top {node[':select-n']}"
        else:
            return f"UNEXPECTED :select-fn {node[':select-fn']}"


    def pretty_filter(self, node) -> str:
        return f"{self.pretty_selector(node)} by {self.pretty_indicator(node[':sort-by-fn'], '____', node[':sort-by-window-days'])}"


    def print_children(self, node, depth=0, parent_node_branch_state: typing.Optional[NodeBranchState] = None, file=None):
        """
        Recursively visits every child node (depth-first)
        and pretty-prints it out.
        """
        if not parent_node_branch_state:
            # current node is :root, there is no higher node
            parent_node_branch_state = self.NodeBranchState(1, [], "")
        parent_node_branch_state = typing.cast(
            self.NodeBranchState, parent_node_branch_state)

        current_node_branch_state = self.advance_branch_state(
            parent_node_branch_state, node)

        def pretty_log(message: str):
            s = "  " * depth

            weight_factor = self.extract_weight_factor(parent_node_branch_state, node)
            if not self.is_weight_node(node) and weight_factor != 1:
                s += f"{weight_factor:.0%} => "

            s += message

            if self.is_asset_node(node):
                s += f" (max: {current_node_branch_state.weight:.1%})"
            print(s, file=file)

        if self.is_root_node(node):
            pretty_log(node[":name"])
        elif self.is_equal_weight_node(node):
            # sometimes children will have :weight (sometimes inserted as a no-op)
            pretty_log("Weight equally:")
        elif self.is_specified_weight_node(node):
            # children will have :weight
            # ':weight': {':num': 88, ':den': 100}, (numerator and denominator)
            pretty_log("Weight accordingly:")
        elif self.is_if_node(node):
            pretty_log("if")
        elif self.is_if_child_node(node):
            if not self.is_conditional_node(node):
                pretty_log("else")
            else:
                pretty_log(f"({self.pretty_condition(node)})")
        elif self.is_group_node(node):
            pretty_log(f"// {node[':name']}")
        elif self.is_filter_node(node):
            pretty_log(self.pretty_filter(node))
        elif self.is_asset_node(node):
            pretty_log(self.get_ticker_of_asset_node(node))
        else:
            pretty_log(f"UNIMPLEMENTED: {node[':step']}")

        for child in self.get_node_children(node):
            self.print_children(child, depth=depth+1,
                           parent_node_branch_state=current_node_branch_state, file=file)


    def convert_to_pretty_format(self, root_node) -> str:
        output = io.StringIO()
        self.print_children(root_node, file=output)
        text = output.getvalue()
        output.close()
        return text


if __name__ == "__main__":
    main()
