import asyncio
import inspect
from collections import defaultdict
from inspect import Signature, _empty, isabstract, isawaitable
from typing import (
    Any,
    Awaitable,
    Callable,
    DefaultDict,
    Dict,
    Optional,
    Set,
    Type,
    Union,
    get_type_hints,
)

from .exception import (
    AliasAlreadyDefined,
    AliasConfigurationError,
    AsyncDependencyError,
    FactoryMissingContextException,
    InvalidFactory,
    InvalidOperationInStrictMode,
    MissingTypeException,
    OverridingServiceException,
)
from .resolver import DynamicResolver, ResolutionContext
from .resolver.dynamic import FactoryResolver
from .resolver.instance import InstanceResolver
from .svc import ActivationScope, Services
from .types import AliasesTypeHint, ContainerProtocol, ServiceLifeStyle, T, Token
from .utils import (
    class_name,
    is_coroutine_fn,
    maybe_promesify_instance,
    needs_promesify,
    to_standard_param_name,
)

FactoryCallableNoArguments = Callable[[], Any]
FactoryCallableSingleArgument = Callable[[ActivationScope], Any]
FactoryCallableTwoArguments = Callable[[ActivationScope, Type], Any]
FactoryCallableType = Union[
    FactoryCallableNoArguments,
    FactoryCallableSingleArgument,
    FactoryCallableTwoArguments,
]


class Container(ContainerProtocol):
    """
    Configuration class for a collection of services.
    """

    __slots__ = ('_map', '_aliases', '_exact_aliases', 'strict')

    def __init__(self, *, strict: bool = False):
        self._map: Dict[Token[Any], Callable] = {}
        self._aliases: DefaultDict[str, Set[Token[Any]]] = defaultdict(set)
        self._exact_aliases: Dict[str, Type] = {}
        self._provider: Optional[Services] = None
        self.strict = strict

    @property
    def provider(self) -> Services:
        if self._provider is None:
            self._provider = self.build_provider()
        return self._provider

    # region: ContainerProtocol implementation

    def register(
        self,
        obj_type: Any,
        sub_type: Any = None,
        instance: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> 'Container':
        """
        Registers a type in this container.
        """
        if instance is not None:
            self.add_instance(instance, declared_class=obj_type)
            return self

        if sub_type is None:
            self._add_exact_transient(obj_type)
        else:
            self.add_transient(obj_type, sub_type)
        return self

    def resolve(
        self,
        obj_type: Union[Type[T], str],
        scope: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Resolves a service by type, obtaining an instance of that type.
        """
        instance = self.provider.get(obj_type, scope=scope)

        # check if fail on coroutine is enabled in kwargs
        if kwargs.get('fail_on_coroutine', True) and (
            needs_promesify(instance, self)
            or inspect.iscoroutine(instance)
            or (isinstance(instance, asyncio.Task) and not instance.done())
        ):
            raise AsyncDependencyError(obj_type)

        # if it's a task and it's done, return the result
        if isinstance(instance, asyncio.Task) and instance.done():
            return instance.result()

        return instance

    def __contains__(self, key: Type) -> bool:
        return key in self._map

    # endregion

    async def aresolve(
        self,
        obj_type: Union[Type[T], str],
        scope: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Resolves a service by type, obtaining an instance of that type.

        If the resulting instance needs await, this method should be used instead of
        `resolve`.
        """
        # first, get the instance synchronously calling the original resolve method
        instance = self.resolve(obj_type, scope, *args, **kwargs, fail_on_coroutine=False)
        instance = maybe_promesify_instance(instance, self)

        if is_coroutine_fn(instance):
            return await instance()
        elif isawaitable(instance):
            return await instance
        else:
            return instance

    def __iter__(self) -> Any:
        yield from self._map.items()

    def bind_types(
        self,
        obj_type: Any,
        concrete_type: Any = None,
        life_style: ServiceLifeStyle = ServiceLifeStyle.TRANSIENT,
    ) -> 'Container':
        try:
            if not issubclass(concrete_type, obj_type):
                raise ValueError(
                    f'Cannot register {class_name(obj_type)} for abstract class '
                    f'{class_name(concrete_type)}'
                )

        except TypeError:
            # ignore, this happens with generic types
            pass
        self._bind(obj_type, DynamicResolver(concrete_type, self, life_style))
        return self

    def add_alias(self, name: str, desired_type: Type) -> 'Container':
        """
        Adds an alias to the set of inferred aliases.

        :param name: parameter name
        :param desired_type: desired type by parameter name
        :return: self
        """
        if self.strict:
            raise InvalidOperationInStrictMode()
        if name in self._aliases or name in self._exact_aliases:
            raise AliasAlreadyDefined(name)
        self._aliases[name].add(desired_type)
        return self

    def add_aliases(self, values: AliasesTypeHint) -> 'Container':
        """
        Adds aliases to the set of inferred aliases.

        :param values: mapping object (parameter name: class)
        :return: self
        """
        for key, value in values.items():
            self.add_alias(key, value)
        return self

    def set_alias(self, name: str, desired_type: Type, override: bool = False) -> 'Container':
        """
        Sets an exact alias for a desired type.

        :param name: parameter name
        :param desired_type: desired type by parameter name
        :param override: whether to override existing values, or throw exception
        :return: self
        """
        if self.strict:
            raise InvalidOperationInStrictMode()
        if not override and name in self._exact_aliases:
            raise AliasAlreadyDefined(name)
        self._exact_aliases[name] = desired_type
        return self

    def set_aliases(self, values: AliasesTypeHint, override: bool = False) -> 'Container':
        """Sets many exact aliases for desired types.

        :param values: mapping object (parameter name: class)
        :param override: whether to override existing values, or throw exception
        :return: self
        """
        for key, value in values.items():
            self.set_alias(key, value, override)
        return self

    def _bind(self, key: Token[Any], value: Any) -> None:
        if key in self._map:
            raise OverridingServiceException(key, value)

        self._map[key] = value

        if self._provider is not None:
            self._provider = None

        key_name = class_name(key)

        if self.strict or '.' in key_name:
            return

        self._aliases[key_name].add(key)
        self._aliases[key_name.lower()].add(key)
        self._aliases[to_standard_param_name(key_name)].add(key)

    def add_instance(self, instance: Any, declared_class: Optional[Type] = None) -> 'Container':
        """
        Registers an exact instance, optionally by declared class.

        :param instance: singleton to be registered
        :param declared_class: optionally, lets define the class used as reference of
        the singleton
        :return: the service collection itself
        """
        self._bind(
            instance.__class__ if not declared_class else declared_class,
            InstanceResolver(instance),
        )
        return self

    def add_singleton(
        self, base_type: Token[Any], concrete_type: Optional[Type] = None
    ) -> 'Container':
        """
        Registers a type by base type, to be instantiated with singleton lifetime.
        If a single type is given, the method `add_exact_singleton` is used.

        :param base_type: registered type. If a concrete type is provided, it must
        inherit the base type.
        :param concrete_type: concrete class
        :return: the service collection itself
        """
        if concrete_type is None:
            return self._add_exact_singleton(base_type)

        return self.bind_types(base_type, concrete_type, ServiceLifeStyle.SINGLETON)

    def add_scoped(self, base_type: Type, concrete_type: Optional[Type] = None) -> 'Container':
        """
        Registers a type by base type, to be instantiated with scoped lifetime.
        If a single type is given, the method `add_exact_scoped` is used.

        :param base_type: registered type. If a concrete type is provided, it must
        inherit the base type.
        :param concrete_type: concrete class
        :return: the service collection itself
        """
        if concrete_type is None:
            return self._add_exact_scoped(base_type)

        return self.bind_types(base_type, concrete_type, ServiceLifeStyle.SCOPED)

    def add_transient(self, base_type: Type, concrete_type: Optional[Type] = None) -> 'Container':
        """
        Registers a type by base type, to be instantiated with transient lifetime.
        If a single type is given, the method `add_exact_transient` is used.

        :param base_type: registered type. If a concrete type is provided, it must
        inherit the base type.
        :param concrete_type: concrete class
        :return: the service collection itself
        """
        if concrete_type is None:
            return self._add_exact_transient(base_type)

        return self.bind_types(base_type, concrete_type, ServiceLifeStyle.TRANSIENT)

    def _add_exact_singleton(self, concrete_type: Token[Any]) -> 'Container':
        """
        Registers an exact type, to be instantiated with singleton lifetime.

        :param concrete_type: concrete class
        :return: the service collection itself
        """
        if isabstract(concrete_type):
            raise ValueError(f'Cannot register abstract class {class_name(concrete_type)}')

        self._bind(
            concrete_type,
            DynamicResolver(concrete_type, self, ServiceLifeStyle.SINGLETON),
        )
        return self

    def _add_exact_scoped(self, concrete_type: Type) -> 'Container':
        """
        Registers an exact type, to be instantiated with scoped lifetime.

        :param concrete_type: concrete class
        :return: the service collection itself
        """
        if isabstract(concrete_type):
            raise ValueError(f'Cannot register abstract class {class_name(concrete_type)}')

        self._bind(concrete_type, DynamicResolver(concrete_type, self, ServiceLifeStyle.SCOPED))
        return self

    def _add_exact_transient(self, concrete_type: Type) -> 'Container':
        """
        Registers an exact type, to be instantiated with transient lifetime.

        :param concrete_type: concrete class
        :return: the service collection itself
        """
        if isabstract(concrete_type):
            raise ValueError(f'Cannot register abstract class {class_name(concrete_type)}')

        self._bind(
            concrete_type,
            DynamicResolver(concrete_type, self, ServiceLifeStyle.TRANSIENT),
        )
        return self

    def add_singleton_by_factory(
        self, factory: FactoryCallableType, return_type: Optional[Type] = None
    ) -> 'Container':
        self.register_factory(factory, return_type, ServiceLifeStyle.SINGLETON)
        return self

    def add_transient_by_factory(
        self, factory: FactoryCallableType, return_type: Optional[Type] = None
    ) -> 'Container':
        self.register_factory(factory, return_type, ServiceLifeStyle.TRANSIENT)
        return self

    def add_scoped_by_factory(
        self, factory: FactoryCallableType, return_type: Optional[Type] = None
    ) -> 'Container':
        self.register_factory(factory, return_type, ServiceLifeStyle.SCOPED)
        return self

    @staticmethod
    def _check_factory(factory: Callable, signature: Signature, handled_type: Type) -> Callable:
        if not callable(factory):
            raise InvalidFactory(handled_type)

        params_len = len(signature.parameters)

        is_async = inspect.iscoroutinefunction(factory) or inspect.isasyncgenfunction(factory)

        if params_len == 0:
            if is_async:
                return AsyncFactoryWrapperNoArgs(factory)
            return FactoryWrapperNoArgs(factory)

        if params_len == 1:
            if is_async:
                return AsyncFactoryWrapperContextArg(factory)
            return FactoryWrapperContextArg(factory)

        if params_len == 2:
            return factory

        raise InvalidFactory(handled_type)

    def register_factory(
        self,
        factory: Callable,
        return_type: Optional[Type],
        life_style: ServiceLifeStyle,
    ) -> None:
        if not callable(factory):
            raise InvalidFactory(return_type)

        sign = Signature.from_callable(factory)
        if return_type is None:
            if sign.return_annotation is _empty:
                raise MissingTypeException()
            return_type = sign.return_annotation

            if isinstance(return_type, str):  # pragma: no cover
                # Python 3.10
                annotations = _get_factory_annotations_or_throw(factory)
                return_type = annotations['return']

        if return_type is None:
            raise ValueError('Return type must be provided')

        self._bind(
            return_type,  # type: ignore
            FactoryResolver(
                return_type, self._check_factory(factory, sign, return_type), life_style
            ),
        )

    def build_provider(self) -> Services:
        """
        Builds and returns a service provider that can be used to activate and obtain
        services.

        The configuration of services is validated at this point, if any service cannot
        be instantiated due to missing dependencies, an exception is thrown inside this
        operation.

        :return: Service provider that can be used to activate and obtain services.
        """
        with ResolutionContext() as context:
            _map: Dict[Token[Any], Type] = {}

            for _type, resolver in self._map.items():
                if isinstance(resolver, DynamicResolver):
                    context.dynamic_chain.clear()

                if _type in context.resolved:
                    # assert _type not in context.resolved, "_map keys must be unique"
                    # check if its in the map
                    if _type in _map:
                        # NB: do not call resolver if one was already prepared for the
                        # type
                        raise OverridingServiceException(_type, resolver)
                    else:
                        resolved = context.resolved[_type]
                else:
                    # add to context so that we don't repeat operations
                    resolved = resolver(context)
                    context.resolved[_type] = resolved

                _map[_type] = resolved

                type_name = class_name(_type)
                if '.' not in type_name:
                    _map[type_name] = _map[_type]

            if not self.strict:
                if self._aliases is None or self._exact_aliases is None:
                    raise AssertionError('Aliases must be set before building the provider')

                # include aliases in the map;
                for name, _types in self._aliases.items():
                    for _type in _types:
                        break
                    _map[name] = self._get_alias_target_type(name, _map, _type)

                for name, _type in self._exact_aliases.items():
                    _map[name] = self._get_alias_target_type(name, _map, _type)

        return Services(_map)

    @staticmethod
    # def _get_alias_target_type(name, _map, _type):
    def _get_alias_target_type(name: str, _map: Dict[Token[Any], Type], _type: Token[Any]) -> Type:
        try:
            return _map[_type]
        except KeyError:
            raise AliasConfigurationError(name, _type)


def _get_factory_annotations_or_throw(factory: Callable) -> Dict[str, Any]:
    factory_locals = getattr(factory, '_locals', None)
    factory_globals = getattr(factory, '_globals', None)

    if factory_locals is None:
        raise FactoryMissingContextException(factory)

    return get_type_hints(factory, globalns=factory_globals, localns=factory_locals)


class FactoryWrapperNoArgs:
    __slots__ = ('factory',)

    def __init__(self, factory: FactoryCallableNoArguments):
        self.factory = factory

    def __call__(self, *_args: Any) -> Any:
        return self.factory()


class FactoryWrapperContextArg:
    __slots__ = ('factory',)

    def __init__(self, factory: FactoryCallableSingleArgument):
        self.factory = factory

    def __call__(self, context: ActivationScope, *_args: Any) -> Any:
        return self.factory(context)


class AsyncFactoryWrapperNoArgs:
    __slots__ = ('factory',)

    def __init__(self, factory: Callable[[], Awaitable[Any]]):
        self.factory = factory

    async def __call__(self, *_args: Any) -> Any:
        res = self.factory()
        if isawaitable(res):
            return await res
        return res


class AsyncFactoryWrapperContextArg:
    __slots__ = ('factory',)

    def __init__(self, factory: Callable[[ActivationScope], Awaitable[Any]]):
        self.factory = factory

    async def __call__(self, context: ActivationScope, *_args: Any) -> Any:
        res = self.factory(context)
        if isawaitable(res):
            return await res
        return res
