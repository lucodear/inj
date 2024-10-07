from enum import Enum
from typing import Any, Dict, Type, TypeVar, Union

try:
    from typing import Protocol
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol

T = TypeVar('T')

Token = Union[Type[T], str]


class ContainerProtocol(Protocol):
    """
    Generic interface of DI Container that can register and resolve services,
    and tell if a type is configured.
    """

    def register(self, obj_type: Token[Any], *args: Any, **kwargs: Any) -> None:
        """Registers a type in the container, with optional arguments."""
        ...

    def resolve(self, obj_type: Token[T], *args: Any, **kwargs: Any) -> T:
        """Activates an instance of the given type, with optional arguments."""
        ...

    def __contains__(self, item: Token[Any]) -> bool:
        """
        Returns a value indicating whether a given type is configured in this container.
        """
        ...


class ServiceLifeStyle(Enum):
    TRANSIENT = 1
    SCOPED = 2
    SINGLETON = 3


AliasesTypeHint = Dict[str, Type]
