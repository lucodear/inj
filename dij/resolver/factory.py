from typing import Any, Callable, Type

from ..svc import ActivationScope


class FactoryTypeProvider:
    __slots__ = ('_type', 'factory')

    def __init__(self, _type: Type, factory: Callable):
        self._type = _type
        self.factory = factory

    def __call__(self, context: ActivationScope, parent_type: Type, *_args: Any) -> Any:
        if not isinstance(context, ActivationScope):
            raise TypeError(f'Expected ActivationScope, got {type(context)}')

        return self.factory(context, parent_type)


class ScopedFactoryTypeProvider:
    __slots__ = ('_type', 'factory')

    def __init__(self, _type: Type, factory: Callable):
        self._type = _type
        self.factory = factory

    def __call__(self, context: ActivationScope, parent_type: Type, *_args: Any) -> Any:
        if context.scoped_services is None:
            raise ValueError('Scoped services are not available')

        if self._type in context.scoped_services:
            return context.scoped_services[self._type]

        instance = self.factory(context, parent_type)
        context.scoped_services[self._type] = instance
        return instance


class SingletonFactoryTypeProvider:
    __slots__ = ('_type', 'factory', 'instance')

    def __init__(self, _type: Type, factory: Callable):
        self._type = _type
        self.factory = factory
        self.instance = None

    def __call__(self, context: ActivationScope, parent_type: Type, *_args: Any) -> Any:
        if self.instance is None:
            self.instance = self.factory(context, parent_type)
        return self.instance
