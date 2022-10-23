import copy
import typing
import edn_format
import json
from . import edn_syntax


def get_root_node_from_path(path: str):
    try:
        # Data is wrapped with "" and has escaped all the "s, this de-escapes
        data_with_wrapping_string_removed = json.load(
            open(path, 'r'))
        root_data_immutable = edn_format.loads(
            data_with_wrapping_string_removed)
        root_data = typing.cast(
            dict, edn_syntax.convert_edn_to_pythonic(root_data_immutable))
        root_node = root_data[":symphony"]
    except:
        root_data_immutable = edn_format.loads(open(path, 'r').read())
        root_node = typing.cast(
            dict, edn_syntax.convert_edn_to_pythonic(root_data_immutable))

    return root_node


def debug_print_node(node):
    new_node = copy.copy(node)
    del new_node[":children"]
    del new_node[":step"]
    print(json.dumps(new_node, indent=4, sort_keys=True))
