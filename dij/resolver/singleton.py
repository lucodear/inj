from typing import Any, Callable, List, Optional, Type


class SingletonTypeProvider:
    __slots__ = ('_type', '_instance', '_args_callbacks')

    def __init__(self, _type: Type, _args_callbacks: Optional[List[Callable]]):
        self._type = _type
        self._args_callbacks = _args_callbacks
        self._instance = None

    def __call__(self, context: Type, *_args: Any) -> Type:
        if self._instance is None:
            self._instance = (
                self._type(*[fn(context, self._type) for fn in self._args_callbacks])
                if self._args_callbacks
                else self._type()
            )

        return self._instance
