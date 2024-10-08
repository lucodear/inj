import inspect
from typing import Any, Callable, Type

from ..svc import ActivationScope
from ..types import ServiceLifeStyle
from ..utils import is_coroutine_fn
from .context import ResolutionContext
from .factory_async import (
    AsyncFactoryTypeProvider,
    AsyncScopedFactoryTypeProvider,
    AsyncSingletonFactoryTypeProvider,
)


class FactoryResolver:
    __slots__ = ('concrete_type', 'factory', 'params', 'life_style')

    def __init__(self, concrete_type: Type, factory: Callable, life_style: ServiceLifeStyle):
        self.factory = factory
        self.concrete_type = concrete_type
        self.life_style = life_style

    def __call__(self, context: ResolutionContext, *_args: Any) -> Any:
        is_async = is_coroutine_fn(self.factory)

        if self.life_style == ServiceLifeStyle.SINGLETON:
            if is_async:
                return AsyncSingletonFactoryTypeProvider(self.concrete_type, self.factory)
            return SingletonFactoryTypeProvider(self.concrete_type, self.factory)

        if self.life_style == ServiceLifeStyle.SCOPED:
            if is_async:
                return AsyncScopedFactoryTypeProvider(self.concrete_type, self.factory)
            return ScopedFactoryTypeProvider(self.concrete_type, self.factory)

        if is_async:
            return AsyncFactoryTypeProvider(self.concrete_type, self.factory)
        return FactoryTypeProvider(self.concrete_type, self.factory)


class FactoryTypeProvider:
    __slots__ = ('_type', 'factory')

    def __init__(self, _type: Type, factory: Callable):
        self._type = _type
        self.factory = factory

    def __call__(self, context: ActivationScope, parent_type: Type, *_args: Any) -> Any:
        if not isinstance(context, ActivationScope):
            raise TypeError(f'Expected ActivationScope, got {type(context)}')

        instance = self.factory(context, parent_type)
        return maybe_solve_generator(instance)


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
        return maybe_solve_generator(instance)


class SingletonFactoryTypeProvider:
    __slots__ = ('_type', 'factory', 'instance')

    def __init__(self, _type: Type, factory: Callable):
        self._type = _type
        self.factory = factory
        self.instance = None

    def __call__(self, context: ActivationScope, parent_type: Type, *_args: Any) -> Any:
        if self.instance is None:
            self.instance = self.factory(context, parent_type)
        return maybe_solve_generator(self.instance)


def maybe_solve_generator(instance: Any) -> Any:
    """
    Check if the instance is a generator and if so, resolve it to the first value and return it.
    If it's not a generator, return the instance as is.
    """

    if inspect.isgenerator(instance):
        return next(instance)
    return instance
