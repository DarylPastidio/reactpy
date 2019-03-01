import json
import asyncio
import inspect
from collections.abc import Mapping

from typing import (
    List,
    Dict,
    Tuple,
    Callable,
    Iterator,
    Union,
    Any,
    Optional,
    AsyncIterator,
)

from .element import Element

try:
    import vdom
except ImportError:
    vdom = None


class RenderError(Exception):
    """An error occured while rendering element models."""


class Layout:
    """Renders the models generated by :class:`Element` objects."""

    __slots__ = ("_update_event", "_update_queue", "_callback_queue", "_root", "_state")

    def __init__(self, root: "Element"):
        if not isinstance(root, Element):
            raise TypeError("Expected an Element, not %r" % root)
        self._state: Dict[str, Dict] = {}
        self._root = root
        self._update_queue: List[Element] = []
        self._update_event = asyncio.Event()
        self._callback_queue: List[Callable] = []
        self._create_element_state(root.id, None)
        self._update(root)

    @property
    def root(self) -> str:
        return self._root.id

    async def apply(self, target: str, handler: str, data: dict):
        try:
            model_state = self._state[target]
            function = model_state["event_handlers"][handler]
        except KeyError:
            pass
        else:
            result = function(**data)
            if inspect.isawaitable(result):
                await result

    async def render(self) -> Tuple[List[str], Dict[str, Dict], List[str]]:
        roots, new = [], {}
        # current element ids
        current = set(self._state)
        for element in await self._updates():
            parent = self._state[element.id]["parent"]
            async for element_id, model in self._render_element(element, parent):
                new[element_id] = model
            roots.append(element.id)
        callbacks = self._callback_queue[:]
        self._callback_queue.clear()
        for cb in callbacks:
            result = cb()
            if inspect.isawaitable(result):
                await result
        # all deleted element ids
        old = list(current.difference(self._state))
        return roots, new, old

    def _callback(self, function: Callable):
        self._callback_queue.append(function)

    def _update(self, element: "Element"):
        self._update_queue.append(element)
        self._update_event.set()

    async def _updates(self) -> List["Element"]:
        await self._update_event.wait()
        self._update_event.clear()
        updates = self._update_queue[:]
        self._update_queue.clear()
        return updates

    async def _render_element(
        self, element: "Element", parent_eid: str
    ) -> AsyncIterator[Tuple[str, Dict]]:
        try:
            element._mount(self)
            model = await element.render()

            if isinstance(model, Element):
                model = {"tagName": "div", "children": [model]}

            eid = element.id
            if self._has_element_state(eid):
                self._reset_element_state(eid)
            else:
                self._create_element_state(eid, parent_eid)

            async for i, m in self._render_model(model, eid):
                yield i, m
        except Exception as error:
            raise RenderError(f"Failed to render {element}") from error

    async def _render_model(
        self, model: Mapping, eid: str
    ) -> AsyncIterator[Tuple[str, Dict]]:
        index = 0
        to_visit: List[Union[Mapping, Element]] = [model]
        while index < len(to_visit):
            node = to_visit[index]
            if isinstance(node, Element):
                async for i, m in self._render_element(node, eid):
                    yield i, m
            elif isinstance(node, Mapping):
                if "children" in node:
                    value = node["children"]
                    if isinstance(value, (list, tuple)):
                        to_visit.extend(value)
                    elif isinstance(value, (Mapping, Element)):
                        to_visit.append(value)
            elif vdom is not None and isinstance(node, vdom.VDOM):
                to_visit.append(_from_vdom(node))
            index += 1
        yield eid, self._load_model(model, eid)

    def _load_model(self, model: Mapping, eid: str):
        model = dict(model)
        children = model["children"] = self._load_model_children(
            model.setdefault("children", []), eid
        )
        model["eventHandlers"] = self._load_event_handlers(
            model.setdefault("eventHandlers", {}), eid
        )
        return model

    def _load_model_children(
        self, children: Union[List, Tuple], eid: str
    ) -> List[Dict]:
        if not isinstance(children, (list, tuple)):
            children = [children]
        loaded_children = []
        for child in children:
            if isinstance(child, Mapping):
                child = {"type": "obj", "data": self._load_model(child, eid)}
            elif isinstance(child, Element):
                child = {"type": "ref", "data": child.id}
            else:
                child = {"type": "str", "data": str(child)}
            loaded_children.append(child)
        return loaded_children

    def _load_event_handlers(
        self, handlers: Dict[str, Callable], key: str
    ) -> Dict[str, str]:
        event_targets = {}
        for event, handler in handlers.items():
            callback_id = str(id(handler))
            params = "-".join(list(inspect.signature(handler).parameters))
            callback_key = "%s_%s" % (callback_id, event)
            if params:
                callback_key += "-" + params
            event_targets[key] = callback_key
            self._state[key]["event_handlers"][callback_id] = handler
        return event_targets

    def _has_element_state(self, eid: str) -> bool:
        return eid in self._state

    def _create_element_state(self, eid: str, parent_eid: Optional[str]):
        if parent_eid is not None and self._has_element_state(parent_eid):
            self._state[parent_eid]["inner_elements"].add(eid)
        self._state[eid] = {
            "parent": parent_eid,
            "inner_elements": set(),
            "event_handlers": {},
        }

    def _reset_element_state(self, eid: str):
        parent_eid = self._state[eid]["parent"]
        self._delete_element_state(eid)
        self._create_element_state(eid, parent_eid)

    def _delete_element_state(self, eid: str):
        old = self._state.pop(eid)
        parent_eid = old["parent"]
        if self._has_element_state(parent_eid):
            self._state[parent_eid]["inner_elements"].remove(eid)
        for i in old["inner_elements"]:
            self._delete_element_state(i)


def _from_vdom(node: vdom.VDOM):
    data = {
        "tagName": node.tag_name,
        "children": node.children,
        "attributes": node.attributes,
    }
    if node.style:
        data["attributes"]["style"] = node.style
    if node.event_handlers:
        data["eventHandlers"] = node.event_handlers
    if node.key:
        data["key"] = node.key
    return data
