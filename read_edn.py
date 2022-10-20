import datetime
import typing
import edn_format
import json


def make_nice(d):
    if type(d) == edn_format.immutable_dict.ImmutableDict:
        return {make_nice(k): make_nice(v) for k, v in d.items()}
    elif type(d) == edn_format.immutable_list.ImmutableList:
        return [make_nice(v) for v in d]
    elif type(d) == edn_format.edn_lex.Keyword:
        return ":" + d.name
    else:
        return d


def main():
    # Data is wrapped with "" and has escaped all the "s, this de-escapes
    data_with_wrapping_string_removed = json.load(open('inputFile.edn', 'r'))
    root_data_immutable = edn_format.loads(data_with_wrapping_string_removed)
    root_data = typing.cast(dict, make_nice(root_data_immutable))

    #
    # Data in root_data:
    #
    # ":uid": "sdfadfddasf",
    # ":capital": 10000,
    # ":apply-taf-fee?": true,
    # ":symphony-benchmarks": [],
    # ":slippage-percent": 0.0005,
    # ":client-commit": "bvcxdfff",
    # ":apply-reg-fee?": true,
    # ":ticker-benchmarks": [
    #     {
    #         ":color": "#F6609F",
    #         ":id": "SPY",
    #         ":checked?": true,
    #         ":type": ":ticker",
    #         ":ticker": "SPY"
    #     }
    # ]
    # print(json.dumps(root_data, indent=4))

    root_rule = root_data[":symphony"]
    #
    # Data in root_rule:
    #
    # ":id": "43refdscxz",
    # ":step": ":root",
    # ":name": "farm fun 99",
    # ":description": "",
    # ":rebalance": ":daily",
    # ":children": [...]
    # print(json.dumps(root_rule, indent=4))

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


def get_founded_date(ticker: str) -> datetime.date:
    # TODO: look values up (I have this in the ETF DB)
    return datetime.date(2017, 7, 1)


def collect_allocateable_assets(node) -> set[str]:
    s = set()
    if node[':step'] == ":asset":
        s.add(node[':ticker'])
        return s  # this is a leaf node, can end here

    for child in node[":children"] if ":children" in node else []:
        s.update(collect_allocateable_assets(child))
    return s


def collect_if_referenced_assets(node) -> set[str]:
    """
    Collects tickers referenced by if-conditions
    """
    s = set()
    if node[':step'] == ":asset":
        # s.add(node[':ticker'])
        return s  # this is a leaf node, can end here
    elif node[':step'] == ":if-child" and not node[":is-else-condition?"]:
        if type(node[':lhs-val']) == str:
            s.add(node[':lhs-val'])
        if not node.get(':rhs-fixed-value?', type(node[':rhs-val']) != str):
            s.add(node[':rhs-val'])

    for child in node[":children"] if ":children" in node else []:
        s.update(collect_if_referenced_assets(child))
    return s


def collect_referenced_assets(node) -> set[str]:
    s = set()
    s.update(collect_if_referenced_assets(node))
    s.update(collect_allocateable_assets(node))
    return s


def print_children(node, depth=0):
    """
    Recursively visits every child node (depth-first)
    and pretty-prints it out.
    """
    # Every node has ":id", maybe ":children", and ":step"
    node_type = node[":step"]
    if node_type == ":root":
        # ':name': str
        # ':description': str
        # ':rebalance': TODO
        print("  " * depth, node[":name"])
    elif node_type == ":wt-cash-equal":
        # ':window-days': Optional[int] TODO: what does it mean?
        print("  " * depth, "Weight equally:")

    elif node_type == ":if":
        # All :children are definitely if-child

        print("  " * depth, "if")
    elif node_type == ":if-child":
        # ':is-else-condition?'

        if node[":is-else-condition?"]:
            print("  " * depth, "else")
        else:
            # ':rhs-fn'
            # ':rhs-fixed-value?'
            # ':rhs-window-days'
            # ':rhs-val'

            # ':lhs-fn'
            # ':lhs-window-days'
            # ':lhs-val'

            # ':comparator'

            # NOTE: parameter if :rhs-fixed-value
            def pretty_fn(fn_string: str) -> str:
                if fn_string == ":relative-strength-index":
                    return "RSI"
                return fn_string

            def pretty_comparison(comparator_string: str) -> str:
                if comparator_string == ":lte":
                    return "≤"
                if comparator_string == ":lt":
                    return "<"
                if comparator_string == ":gte":
                    return "≥"
                if comparator_string == ":gt":
                    return ">"
                return comparator_string

            lhs = node[':lhs-val'] if type(
                node[':lhs-val']) != str else f"{pretty_fn(node[':lhs-fn'])}({node[':lhs-val']}, {node[':lhs-window-days']})"
            rhs = node[':rhs-val'] if node.get(':rhs-fixed-value?', type(
                node[':rhs-val']) != str) else f"{pretty_fn(node[':rhs-fn'])}({node[':rhs-val']}, {node[':rhs-window-days']})"

            print("  " * depth, lhs,
                  pretty_comparison(node[':comparator']), rhs)

    elif node_type == ":group":
        # ':name'
        # ':collapsed?'
        print("  " * depth, f"// {node[':name']}")
    elif node_type == ":filter":
        # ':select?'
        # ':select-fn'
        # ':select-n'
        # ':sort-by-fn'
        # ':sort-by-window-days'
        # ':weight'
        # ':sort-by?'
        # ':collapsed-specified-weight?'
        print("  " * depth, node_type,
              "{TODO express selection/sorting/weighting criteria}")
    elif node_type == ":asset":
        # ':name'
        # ':ticker'
        # ':has_marketcap'
        # ':exchange'
        # ':price'
        # ':dollar_volume'
        print("  " * depth, node[":ticker"])
    else:
        print("  " * depth, "UNIMPLEMENTED:", node_type)

    for child in node[":children"] if ":children" in node else []:
        print_children(child, depth=depth+1)


if __name__ == "__main__":
    main()
