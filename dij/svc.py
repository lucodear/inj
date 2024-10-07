from inspect import _empty
from types import TracebackType
from typing import Any, Callable, Dict, Optional, Type, Union, cast, get_type_hints

from .exception import (
    CannotResolveTypeException,
    FactoryMissingContextException,
    OverridingServiceException,
)
from .types import T, Token
from .utils import class_name


class ActivationScope:
    __slots__ = ('scoped_services', 'provider')

    def __init__(
        self,
        provider: Optional['Services'] = None,
        scoped_services: Optional[Dict[Union[Type[Any], str], Any]] = None,
    ):
        self.provider = provider or Services()
        self.scoped_services = scoped_services or {}

    def __enter__(self) -> 'ActivationScope':
        if self.scoped_services is None:
            self.scoped_services = {}
        return self

    def __exit__(
        self,
        exctype: Optional[Type[BaseException]],
        excinst: Optional[BaseException],
        exctb: Optional[TracebackType],
    ) -> None:
        self.dispose()

    def get(
        self,
        desired_type: Union[Type[T], str],
        scope: Optional['ActivationScope'] = None,
        *,
        default: Optional[Any] = ...,
    ) -> Optional[T]:
        if not self.provider:
            return None
        return self.provider.get(desired_type, scope or self, default=default)

    def dispose(self) -> None:
        if self.provider:
            self.provider = None

        if self.scoped_services:
            self.scoped_services.clear()
            self.scoped_services = None


def _get_factory_annotations_or_throw(factory: Callable) -> Dict[str, Any]:
    factory_locals = getattr(factory, '_locals', None)
    factory_globals = getattr(factory, '_globals', None)

    if factory_locals is None:
        raise FactoryMissingContextException(factory)

    return get_type_hints(factory, globalns=factory_globals, localns=factory_locals)


class Dependency:
    __slots__ = ('name', 'annotation')

    def __init__(self, name: str, annotation: Any):
        self.name = name
        self.annotation = annotation


class Services:
    """
    Provides methods to activate instances of classes, by cached activator functions.
    """

    __slots__ = '_map'

    def __init__(self, services_map: Optional[Dict[Token[Any], Callable]] = None):
        if services_map is None:
            services_map = {}
        self._map = services_map

    def __contains__(self, item: Token[Any]) -> bool:
        return item in self._map

    def __getitem__(self, item: Token[Any]) -> Any:
        return self.get(item)

    def __setitem__(self, key: Token[Any], value: Any) -> None:
        self.set(key, value)

    def set(self, new_type: Token[Any], value: Any) -> None:
        """
        Sets a new service of desired type, as singleton.
        This method exists to increase interoperability of Services class (with dict).

        :param new_type:
        :param value:
        :return:
        """
        type_name = class_name(new_type)
        if new_type in self._map or (not isinstance(new_type, str) and type_name in self._map):
            raise OverridingServiceException(new_type, value)

        def resolver(_context: Any, _desired_type: Any) -> Any:
            return value

        self._map[new_type] = resolver
        if not isinstance(new_type, str):
            self._map[type_name] = resolver

    def get(
        self,
        desired_type: Token[T],
        scope: Optional[ActivationScope] = None,
        *,
        default: Optional[Any] = ...,
    ) -> T:
        """
        Gets a service of the desired type, returning an activated instance.

        :param desired_type: desired service type.
        :param context: optional context, used to handle scoped services.
        :return: an instance of the desired type
        """
        if scope is None:
            scope = ActivationScope(self)

        resolver = self._map.get(desired_type)
        scoped_service = (
            scope.scoped_services.get(desired_type) if scope and scope.scoped_services else None
        )

        value = (
            scoped_service
            if scoped_service
            else resolver(scope, desired_type)
            if resolver
            else None
        )

        if not value:
            if default is not ...:
                return cast(T, default)
            raise CannotResolveTypeException(desired_type)

        return cast(T, value)

    def _get_getter(self, key: str, param: Dependency) -> Callable:
        if param.annotation is _empty:

            def getter(context: ActivationScope) -> Any:
                return self.get(key, context)

        else:

            def getter(context: ActivationScope) -> Any:
                return self.get(param.annotation, context)

        getter.__name__ = f'<getter {key}>'
        return getter
