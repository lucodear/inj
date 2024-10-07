import re
from typing import Type, Union


def class_name(input_type: Union[Type, str]) -> str:
    if isinstance(input_type, str):
        return input_type

    if input_type in {list, set} and str(type(input_type) == "<class 'types.GenericAlias'>"):  # noqa: E721
        # for Python 3.9 list[T], set[T]
        return str(input_type)
    try:
        return input_type.__name__
    except AttributeError:
        # for example, this is the case for List[str], Tuple[str, ...], etc.
        return str(input_type)


_FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
_ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')


def to_standard_param_name(name: str) -> str:
    value = _ALL_CAP_RE.sub(r'\1_\2', _FIRST_CAP_RE.sub(r'\1_\2', name)).lower()
    if value.startswith('i_'):
        return 'i' + value[2:]
    return value
