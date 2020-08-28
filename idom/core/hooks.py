import asyncio
import inspect
from functools import lru_cache
from threading import get_ident as get_thread_id
from typing import (
    Sequence,
    cast,
    Dict,
    Any,
    TypeVar,
    Callable,
    Tuple,
    Awaitable,
    Optional,
    Generic,
    Union,
    NamedTuple,
    List,
    overload,
)

from .element import AbstractElement


__all__ = [
    "use_update",
    "use_state",
    "use_memo",
    "use_lru_cache",
]


def use_update() -> Callable[[], None]:
    return current_hook().schedule_render


_StateType = TypeVar("_StateType")


class _State:
    __slots__ = "current"


def use_state(
    value: Union[_StateType, Callable[[], _StateType]],
) -> Tuple[
    _StateType, Callable[[Union[_StateType, Callable[[_StateType], _StateType]]], None]
]:
    hook = current_hook()
    state: Dict[str, Any] = hook.use_state(_State)
    update = use_update()

    try:
        current = state.current
    except AttributeError:
        if callable(value):
            current = state.current = value()
        else:
            current = state.current = value

    def set_state(new: Union[_StateType, Callable[[_StateType], _StateType]]) -> None:
        if callable(new):
            next_state = new(current)
        else:
            next_state = new
        if next_state is not current:
            state.current = next_state
            update()

    return current, set_state


class Ref(Generic[_StateType]):

    __slots__ = "current"

    def __init__(self, value: _StateType) -> None:
        self.current = value


def use_ref(value: _StateType) -> Ref[_StateType]:
    return use_state(Ref(value))[0]


_EffectCoro = Callable[[], Awaitable[None]]
_EffectFunc = Callable[[Callable[..., None]], None]
_Effect = Union[_EffectCoro, _EffectFunc]


@overload
def use_effect(
    function: None, args: Optional[Sequence[Any]]
) -> Callable[[_Effect], None]:
    ...


@overload
def use_effect(function: _Effect, args: Optional[Sequence[Any]]) -> None:
    ...


def use_effect(
    function: Optional[_Effect] = None,
    args: Optional[Sequence[Any]] = None,
) -> Optional[Callable[[_Effect], None]]:
    memoize = use_memo(args=args)

    def setup(function: _Effect) -> None:
        def _register_effect() -> None:
            hook = current_hook()

            if inspect.iscoroutinefunction(function):

                def effect() -> None:
                    future = asyncio.ensure_future(function())

                    def clean():
                        if future.done():
                            future.result()
                        else:
                            future.cancel()

                    hook.use_effect(clean, "will_render", "will_unmount")

            else:

                def effect() -> None:
                    def clean(_function_, *args, **kwargs):
                        hook.use_effect(
                            lambda: _function_(*args, **kwargs),
                            "will_render",
                            "will_unmount",
                        )

                    function(clean)

            return hook.use_effect(effect, "did_render")

        return memoize(_register_effect)

    if function is not None:
        return setup(function)
    else:
        return setup


_ActionType = TypeVar("_ActionType")


def use_reducer(
    reducer: Callable[[_StateType, _ActionType], _StateType],
    state: _StateType,
) -> Tuple[_StateType, Callable[[_ActionType], None]]:
    state, set_state = use_state(state)

    def dispatch(action: _ActionType) -> None:
        set_state(reducer(state, action))

    return state, dispatch


_MemoValue = TypeVar("_MemoValue")


@overload
def use_memo(
    function: None, args: Optional[Sequence[Any]]
) -> Callable[[Callable[[], _MemoValue]], _MemoValue]:
    ...


@overload
def use_memo(
    function: Callable[[], _MemoValue], args: Optional[Sequence[Any]]
) -> _MemoValue:
    ...


def use_memo(
    function: Optional[Callable[[], _MemoValue]] = None,
    args: Optional[Sequence[Any]] = None,
) -> Union[_MemoValue, Callable[[Callable[[], _MemoValue]], _MemoValue]]:
    hook = current_hook()
    cache: Dict[int, _MemoValue] = hook.use_state(dict)

    if not args:

        def setup(function: Callable[[], _MemoValue]) -> _MemoValue:
            return function()

    else:

        def setup(function: Callable[[], _MemoValue]) -> _MemoValue:
            key = hash(tuple(args))
            if key in cache:
                result = cache[key]
            else:
                cache.clear()
                result = cache[key] = function()
            return result

    if function is not None:
        return setup(function)
    else:
        return setup


_CallbackFunc = TypeVar("_CallbackFunc", bound=Callable[..., Any])


@overload
def use_callback(
    function: None, args: Optional[Sequence[Any]]
) -> Callable[[_Effect], None]:
    ...


@overload
def use_callback(function: _CallbackFunc, args: Optional[Sequence[Any]]) -> None:
    ...


def use_callback(
    function: Optional[_CallbackFunc] = None,
    args: Optional[Sequence[Any]] = None,
) -> Optional[Callable[[_CallbackFunc], None]]:
    memoize = use_memo(args=args)

    def use_setup(function: _CallbackFunc) -> _CallbackFunc:
        return memoize(lambda: function)

    return use_setup


_LruFunc = TypeVar("_LruFunc")


def use_lru_cache(
    function: _LruFunc, maxsize: Optional[int] = 128, typed: bool = False
) -> _LruFunc:
    return cast(_LruFunc, current_hook().use_state(lru_cache(maxsize, typed), function))


_current_life_cycle_hook: Dict[int, "LifeCycleHook"] = {}


def current_hook() -> "LifeCycleHook":
    """Get the current :class:`LifeCycleHook`"""
    try:
        return _current_life_cycle_hook[get_thread_id()]
    except KeyError as error:
        msg = "No life cycle hook is active. Are you rendering in a layout?"
        raise RuntimeError(msg) from error


class _EventEffects(NamedTuple):
    will_render: List[Callable[[], Any]]
    did_render: List[Callable[[], Any]]
    will_unmount: List[Callable[[], Any]]


class LifeCycleHook:
    """Defines the life cycle of a layout element.

    Elements can request access to their own life cycle events and state, while layouts
    drive the life cycle forward by triggering events.
    """

    __slots__ = (
        "element",
        "_schedule_render_callback",
        "_schedule_render_later",
        "_current_state_index",
        "_state",
        "_render_is_scheduled",
        "_rendered_atleast_once",
        "_is_rendering",
        "_event_effects",
        "__weakref__",
    )

    def __init__(
        self,
        element: AbstractElement,
        schedule_render: Callable[[AbstractElement], None],
    ) -> None:
        self.element = element
        self._schedule_render_callback = schedule_render
        self._schedule_render_later = False
        self._render_is_scheduled = False
        self._is_rendering = False
        self._rendered_atleast_once = False
        self._current_state_index = 0
        self._state: Tuple[Any, ...] = ()
        self._event_effects = _EventEffects([], [], [])

    def schedule_render(self) -> None:
        if self._is_rendering:
            self._schedule_render_later = True
        elif not self._render_is_scheduled:
            self._schedule_render()
        return None

    def use_state(
        self, _function_: Callable[..., _StateType], *args: Any, **kwargs: Any
    ) -> _StateType:
        if not self._rendered_atleast_once:
            # since we're not intialized yet we're just appending state
            result = _function_(*args, **kwargs)
            self._state += (result,)
        else:
            # once finalized we iterate over each succesively used piece of state
            result = self._state[self._current_state_index]
        self._current_state_index += 1
        return result

    def use_effect(self, function: Callable[[], None], *events) -> None:
        for e in events:
            getattr(self._event_effects, e).append(function)

    def element_will_render(self) -> None:
        """The element is about to render"""
        self._render_is_scheduled = False
        self._is_rendering = True

        for effect in self._event_effects.will_render:
            effect()

        self._event_effects.will_render.clear()
        self._event_effects.will_unmount.clear()

    def element_did_render(self) -> None:
        """The element completed a render"""
        for effect in self._event_effects.did_render:
            effect()
        self._event_effects.did_render.clear()

        self._is_rendering = False
        if self._schedule_render_later:
            self._schedule_render()
        self._rendered_atleast_once = True
        self._current_state_index = 0

    def element_will_unmount(self) -> None:
        """The element is about to be removed from the layout"""
        for effect in self._event_effects.will_unmount:
            effect()
        self._event_effects.will_unmount.clear()

    def set_current(self) -> None:
        """Set this hook as the active hook in this thread

        This method is called by a layout before entering the render method
        of this hook's associated element.
        """
        _current_life_cycle_hook[get_thread_id()] = self

    def unset_current(self) -> None:
        """Unset this hook as the active hook in this thread"""
        # this assertion should never fail - primarilly useful for debug
        assert _current_life_cycle_hook[get_thread_id()] is self
        del _current_life_cycle_hook[get_thread_id()]

    def _schedule_render(self) -> None:
        self._render_is_scheduled = True
        self._schedule_render_callback(self.element)
