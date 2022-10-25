import pprint
import edn_format

from . import manual_testing


def convert_edn_to_immutable_value(d):
    if type(d) == edn_format.immutable_dict.ImmutableDict:
        return tuple([(convert_edn_to_immutable_value(k), convert_edn_to_immutable_value(v))
                      for k, v in d.items()])
    else:
        return convert_edn_to_pythonic(d)


def convert_edn_to_pythonic(d):
    if type(d) == edn_format.immutable_dict.ImmutableDict:
        return {convert_edn_to_immutable_value(k): convert_edn_to_pythonic(v) for k, v in d.items()}
    elif type(d) == edn_format.immutable_list.ImmutableList:
        return [convert_edn_to_pythonic(v) for v in d]
    elif type(d) == edn_format.edn_lex.Keyword:
        return ":" + d.name
    else:
        return d


def main():
    pprint.pprint(manual_testing.get_root_node_from_path("inputs/weird.edn"))
