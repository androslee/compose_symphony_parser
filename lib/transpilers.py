import abc

from . import human, vectorbt


class Transpiler():
    @abc.abstractstaticmethod
    def convert_to_string(cls, root_node: dict) -> str:
        raise NotImplementedError()


class HumanTextTranspiler():
    @staticmethod
    def convert_to_string(root_node: dict) -> str:
        return human.convert_to_pretty_format(root_node)


class VectorBTTranspiler():
    @staticmethod
    def convert_to_string(root_node: dict) -> str:
        return vectorbt.convert_to_vectorbt(root_node)
