import sys
from inspect import Signature, _empty, isabstract, isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Mapping,
    Optional,
    Type,
    Union,
    get_type_hints,
)

from ..exception import (
    CannotResolveParameterException,
    CircularDependencyException,
    UnsupportedUnionTypeException,
)
from ..svc import Dependency
from ..types import ServiceLifeStyle, Token
from ..utils import class_name
from .context import ResolutionContext
from .factory import FactoryResolver
from .singleton import SingletonTypeProvider
from .type import ArgsTypeProvider, ScopedArgsTypeProvider, ScopedTypeProvider, TypeProvider

if TYPE_CHECKING:
    from ..container import Container

if sys.version_info >= (3, 8):  # pragma: no cover
    try:
        from typing import _no_init_or_replace_init as _no_init  # type: ignore
    except ImportError:  # pragma: no cover
        from typing import _no_init  # type: ignore


class DynamicResolver:
    __slots__ = ('_concrete_type', 'services', 'life_style')

    def __init__(
        self, concrete_type: Token[Any], services: 'Container', life_style: ServiceLifeStyle
    ):
        if not isclass(concrete_type):
            raise TypeError(f'Expected a class, but got: {concrete_type}')

        if isabstract(concrete_type):
            raise TypeError(f'Cannot resolve an abstract class: {class_name(concrete_type)}')

        self._concrete_type = concrete_type
        self.services = services
        self.life_style = life_style

    @property
    def concrete_type(self) -> Type:
        return self._concrete_type

    def _get_resolver(self, desired_type: Token[Any], context: ResolutionContext) -> Any:
        # NB: the following two lines are important to ensure that singletons
        # are instantiated only once per service provider
        # to not repeat operations more than once
        if desired_type in context.resolved:
            return context.resolved[desired_type]

        reg = self.services._map.get(desired_type)

        if reg is None:
            raise ValueError(f'A resolver for type {class_name(desired_type)} is not configured')

        resolver = reg(context)

        # add the resolver to the context, so we can find it
        # next time we need it
        context.resolved[desired_type] = resolver
        return resolver

    def _get_resolvers_for_parameters(
        self,
        concrete_type: Type,
        context: ResolutionContext,
        params: Mapping[str, Dependency],
    ) -> list:
        fns = []
        services = self.services

        for param_name, param in params.items():
            if param_name in ('self', 'args', 'kwargs'):
                continue

            param_type = param.annotation

            if hasattr(param_type, '__origin__') and param_type.__origin__ is Union:
                # NB: we could cycle through possible types using: param_type.__args__
                # Right now Union and Optional types resolution is not implemented,
                # but at least Optional could be supported in the future
                raise UnsupportedUnionTypeException(param_name, concrete_type)

            if param_type is _empty:
                if services.strict:
                    raise CannotResolveParameterException(param_name, concrete_type)

                # support for exact, user defined aliases, without ambiguity
                exact_alias = services._exact_aliases.get(param_name)

                if exact_alias:
                    param_type = exact_alias
                else:
                    aliases = services._aliases[param_name]

                    if aliases:
                        if not len(aliases) == 1:
                            raise ValueError('Configured aliases cannot be ambiguous')
                        for param_type in aliases:
                            break

            if param_type not in services._map:
                raise CannotResolveParameterException(param_name, concrete_type)

            param_resolver = self._get_resolver(param_type, context)
            fns.append(param_resolver)
        return fns

    def _resolve_by_init_method(self, context: ResolutionContext) -> Any:
        sig = Signature.from_callable(self.concrete_type.__init__)
        params = {key: Dependency(key, value.annotation) for key, value in sig.parameters.items()}

        if sys.version_info >= (3, 10):  # pragma: no cover
            # Python 3.10
            annotations = get_type_hints(
                self.concrete_type.__init__,
                vars(sys.modules[self.concrete_type.__module__]),
                _get_obj_locals(self.concrete_type),
            )
            for key, value in params.items():
                if key in annotations:
                    value.annotation = annotations[key]

        concrete_type = self.concrete_type

        if len(params) == 1 and next(iter(params.keys())) == 'self':
            if self.life_style == ServiceLifeStyle.SINGLETON:
                return SingletonTypeProvider(concrete_type, None)

            if self.life_style == ServiceLifeStyle.SCOPED:
                return ScopedTypeProvider(concrete_type)

            return TypeProvider(concrete_type)

        fns = self._get_resolvers_for_parameters(concrete_type, context, params)

        if self.life_style == ServiceLifeStyle.SINGLETON:
            return SingletonTypeProvider(concrete_type, fns)

        if self.life_style == ServiceLifeStyle.SCOPED:
            return ScopedArgsTypeProvider(concrete_type, fns)

        return ArgsTypeProvider(concrete_type, fns)

    def _ignore_class_attribute(self, key: str, value: Any) -> bool:
        """
        Returns a value indicating whether a class attribute should be ignored for
        dependency resolution, by name and value.
        It's ignored if it's a ClassVar or if it's already initialized explicitly.
        """
        is_classvar = getattr(value, '__origin__', None) is ClassVar
        is_initialized = getattr(self.concrete_type, key, None) is not None

        return is_classvar or is_initialized

    def _has_default_init(self) -> bool:
        init = getattr(self.concrete_type, '__init__', None)

        if init is object.__init__:
            return True

        if sys.version_info >= (3, 8):  # pragma: no cover
            if init is _no_init:
                return True
        return False

    def _resolve_by_annotations(
        self, context: ResolutionContext, annotations: Dict[str, Type]
    ) -> Any:
        params = {
            key: Dependency(key, value)
            for key, value in annotations.items()
            if not self._ignore_class_attribute(key, value)
        }
        concrete_type = self.concrete_type

        fns = self._get_resolvers_for_parameters(concrete_type, context, params)
        resolvers = {}

        for i, name in enumerate(params.keys()):
            resolvers[name] = fns[i]

        return get_annotations_type_provider(
            self.concrete_type, resolvers, self.life_style, context
        )

    def __call__(self, context: ResolutionContext, *_args: Any) -> Any:
        concrete_type = self.concrete_type

        chain = context.dynamic_chain
        chain.append(concrete_type)

        if self._has_default_init():
            annotations = get_type_hints(
                concrete_type,
                vars(sys.modules[concrete_type.__module__]),
                _get_obj_locals(concrete_type),
            )

            if annotations:
                try:
                    return self._resolve_by_annotations(context, annotations)
                except RecursionError:
                    raise CircularDependencyException(chain[0], concrete_type)

            return FactoryResolver(
                concrete_type, _get_plain_class_factory(concrete_type), self.life_style
            )(context)

        try:
            return self._resolve_by_init_method(context)
        except RecursionError:
            raise CircularDependencyException(chain[0], concrete_type)


def _get_obj_locals(obj: Any) -> Optional[Dict[str, Any]]:
    return getattr(obj, '_locals', None)


def _get_plain_class_factory(concrete_type: Type) -> Callable:
    def factory(*args: Any) -> Any:
        return concrete_type()

    return factory


def get_annotations_type_provider(
    concrete_type: Type,
    resolvers: Mapping[str, Callable],
    life_style: ServiceLifeStyle,
    resolver_context: ResolutionContext,
) -> Any:
    def factory(context: ResolutionContext, parent_type: Type) -> Any:
        instance = concrete_type()
        for name, resolver in resolvers.items():
            setattr(instance, name, resolver(context, parent_type))
        return instance

    return FactoryResolver(concrete_type, factory, life_style)(resolver_context)
