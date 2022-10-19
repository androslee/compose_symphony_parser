import edn_format
import json


def main():
    # Data is wrapped with "" and has escaped all the "s, this de-escapes
    data_with_wrapping_string_removed = json.load(open('inputFile.edn', 'r'))
    data = edn_format.loads(data_with_wrapping_string_removed)

    print(type(data))
    # <class 'edn_format.immutable_dict.ImmutableDict'>
    # So you can't edit these object, only read.

    for k, v in data.items():
        print(k)


if __name__ == "__main__":
    main()
