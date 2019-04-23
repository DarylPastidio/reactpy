import asyncio
from collections.abc import Mapping

from typing import List, Dict, Tuple, Callable, Union, Any, Set, Optional, AsyncIterator

from .element import Element
from .helpers import EventHandler
from .utils import to_coroutine

try:
    import vdom
except ImportError:
    vdom = None


RenderType = Tuple[List[str], Dict[str, Dict], List[str]]


class RenderError(Exception):
    """An error occured while rendering element models."""


class Layout:
    """Renders the models generated by :class:`Element` objects."""

    __slots__ = (
        "_loop",
        "_render_semaphore",
        "_update_queue",
        "_animate_queue",
        "_rendering",
        "_root",
        "_state",
    )

    def __init__(self, root: "Element", loop: asyncio.AbstractEventLoop = None):
        if loop is None:
            loop = asyncio.get_event_loop()
        if not isinstance(root, Element):
            raise TypeError("Expected an Element, not %r" % root)
        self._loop = loop
        self._state: Dict[str, Dict] = {}
        self._root = root
        self._update_queue: List[Element] = []
        self._render_semaphore = asyncio.Semaphore(1, loop=loop)
        self._animate_queue: List[Callable] = []
        self._create_element_state(root.id, None)
        self._rendering = False
        self.update(root)

    @property
    def loop(self):
        return self._loop

    @property
    def root(self) -> str:
        return self._root.id

    async def apply(self, target: str, handler: str, data: dict):
        if target in self._state:
            # It is possible for an element in the frontend to produce an event
            # associated with a backend model that has been deleted. We only handle
            # events if the element exists in the backend.
            model_state = self._state[target]
            # If the element exists but the handler doesn't then something went wrong.
            # So we allow the potential KeyError.
            event_handler = model_state["event_handlers"][handler]
            await event_handler(data)

    def animate(self, function: Callable):
        self._animate_queue.append(to_coroutine(function))
        if self._render_semaphore.locked():
            # We don't want to release more than once because
            # all changes are renderer in one go. Multiple releases
            # could cause another render even though there were no
            # no updates from the last.
            self._render_semaphore.release()

    def update(self, element: "Element"):
        self._update_queue.append(element)
        if self._render_semaphore.locked():
            # We don't want to release more than once because
            # all changes are renderer in one go. Multiple releases
            # could cause another render even though there were no
            # no updates from the last.
            self._render_semaphore.release()

    async def render(self) -> RenderType:
        if self._rendering:
            raise RuntimeError("Layout is already awaiting a render.")
        else:
            self._rendering = True

        await self._render_semaphore.acquire()

        # current element ids
        current: Set[str] = set(self._state)

        callbacks = self._animate_queue[:]
        self._animate_queue.clear()
        await asyncio.gather(*[cb() for cb in callbacks])

        # root elements which updated
        roots: List[str] = []
        # all element updates
        new: Dict[str, Dict] = {}

        updates = self._update_queue[:]
        self._update_queue.clear()

        for element in updates:
            parent = self._state[element.id]["parent"]
            async for element_id, model in self._render_element(element, parent):
                new[element_id] = model
            roots.append(element.id)

        # all deleted element ids
        old: List[str] = list(current.difference(self._state))

        self._rendering = False

        return roots, new, old

    async def _render_element(
        self, element: "Element", parent_element_id: str
    ) -> AsyncIterator[Tuple[str, Dict]]:
        try:
            if not element.mounted():
                element.mount(self)

            model = await element.render()

            if isinstance(model, Element):
                model = {"tagName": "div", "children": [model]}

            element_id = element.id
            if self._has_element_state(element_id):
                self._reset_element_state(element_id)
            else:
                self._create_element_state(element_id, parent_element_id)

            async for i, m in self._render_model(model, element_id):
                yield i, m
        except Exception as error:
            raise RenderError(f"Failed to render {element}") from error

    async def _render_model(
        self, model: Mapping, element_id: str
    ) -> AsyncIterator[Tuple[str, Dict]]:
        index = 0
        to_visit: List[Union[Mapping, Element]] = [model]
        while index < len(to_visit):
            node = to_visit[index]
            if isinstance(node, Element):
                async for i, m in self._render_element(node, element_id):
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
        yield element_id, self._load_model(model, element_id)

    def _load_model(self, model: Mapping, element_id: str):
        model = dict(model)
        if "children" in model:
            model["children"] = self._load_model_children(model["children"], element_id)
        if "eventHandlers" in model:
            model["eventHandlers"] = self._load_event_handlers(
                model["eventHandlers"], element_id
            )
        return model

    def _load_model_children(
        self, children: Union[List, Tuple], element_id: str
    ) -> List[Dict]:
        if not isinstance(children, (list, tuple)):
            children = [children]
        loaded_children = []
        for child in children:
            if isinstance(child, Mapping):
                child = {"type": "obj", "data": self._load_model(child, element_id)}
            elif isinstance(child, Element):
                child = {"type": "ref", "data": child.id}
            else:
                child = {"type": "str", "data": str(child)}
            loaded_children.append(child)
        return loaded_children

    def _load_event_handlers(
        self, handlers: Dict[str, Callable], element_id: str
    ) -> Dict[str, str]:
        event_targets = {}
        for event, handler in handlers.items():
            if not isinstance(handler, EventHandler):
                handler = EventHandler(handler, event)
            handler_specification = event_targets[element_id] = handler.serialize()
            self._state[element_id]["event_handlers"][handler_specification] = handler
        return event_targets

    def _has_element_state(self, element_id: str) -> bool:
        return element_id in self._state

    def _create_element_state(self, element_id: str, parent_element_id: Optional[str]):
        if parent_element_id is not None and self._has_element_state(parent_element_id):
            self._state[parent_element_id]["inner_elements"].add(element_id)
        self._state[element_id] = {
            "parent": parent_element_id,
            "inner_elements": set(),
            "event_handlers": {},
        }

    def _reset_element_state(self, element_id: str):
        parent_element_id = self._state[element_id]["parent"]
        self._delete_element_state(element_id)
        self._create_element_state(element_id, parent_element_id)

    def _delete_element_state(self, element_id: str):
        old = self._state.pop(element_id)
        parent_element_id = old["parent"]
        if self._has_element_state(parent_element_id):
            self._state[parent_element_id]["inner_elements"].remove(element_id)
        for i in old["inner_elements"]:
            self._delete_element_state(i)


def _from_vdom(node: Any):
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
