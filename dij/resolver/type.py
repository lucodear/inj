from typing import Any, Callable, List, Type

from ..svc import ActivationScope


class ArgsTypeProvider:
    __slots__ = ('_type', '_args_callbacks')

    def __init__(self, _type: Type, _args_callbacks: List[Callable]):
        self._type = _type
        self._args_callbacks = _args_callbacks

    def __call__(self, context: ActivationScope, *_args: Any) -> Any:
        return self._type(*[fn(context, self._type) for fn in self._args_callbacks])


class ScopedArgsTypeProvider:
    __slots__ = ('_type', '_args_callbacks')

    def __init__(self, _type: Type, _args_callbacks: List[Callable]):
        self._type = _type
        self._args_callbacks = _args_callbacks

    def __call__(self, context: ActivationScope, *_args: Any) -> Any:
        if context.scoped_services is None:
            raise ValueError('Scoped services are not available')

        if self._type in context.scoped_services:
            return context.scoped_services[self._type]

        service = self._type(*[fn(context, self._type) for fn in self._args_callbacks])
        context.scoped_services[self._type] = service
        return service


class ScopedTypeProvider:
    __slots__ = ('_type',)

    def __init__(self, _type: Type):
        self._type = _type

    def __call__(self, context: ActivationScope, *_args: Any) -> Any:
        if context.scoped_services is None:
            raise ValueError('Scoped services are not available')

        if self._type in context.scoped_services:
            return context.scoped_services[self._type]

        service = self._type()
        context.scoped_services[self._type] = service
        return service


class TypeProvider:
    __slots__ = ('_type',)

    def __init__(self, _type: Type):
        self._type = _type

    def __call__(self, *_args: Any) -> Any:
        return self._type()
