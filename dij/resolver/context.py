from types import TracebackType
from typing import Optional, Type


class ResolutionContext:
    __slots__ = ('resolved', 'dynamic_chain')
    __deletable__ = ('resolved',)

    def __init__(self) -> None:
        self.resolved = {}
        self.dynamic_chain = []

    def __enter__(self) -> 'ResolutionContext':
        return self

    def __exit__(
        self,
        exctype: Optional[Type[BaseException]],
        excinst: Optional[BaseException],
        exctb: Optional[TracebackType],
    ) -> None:
        self.dispose()

    def dispose(self) -> None:
        del self.resolved
        self.dynamic_chain.clear()
