import edn_format


def convert_edn_to_pythonic(d):
    if type(d) == edn_format.immutable_dict.ImmutableDict:
        return {convert_edn_to_pythonic(k): convert_edn_to_pythonic(v) for k, v in d.items()}
    elif type(d) == edn_format.immutable_list.ImmutableList:
        return [convert_edn_to_pythonic(v) for v in d]
    elif type(d) == edn_format.edn_lex.Keyword:
        return ":" + d.name
    else:
        return d
