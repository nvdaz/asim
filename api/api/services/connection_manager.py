import asyncio
import secrets
from asyncio import Task
from typing import Any, Callable, Coroutine

from bson import ObjectId

from api.services.chat_service import ChatState


class ConnectionManager:
    _on_change: dict[str, Callable[[ChatState], None]] = {}
    _listeners: dict[ObjectId, Task] = {}
    _actions: dict[ObjectId, tuple[ChatState, dict[str, Task]]] = {}

    def _add_listener(self, chat_state: ChatState):
        if chat_state.id not in self._listeners:

            async def listen():
                while True:
                    await chat_state.wait_for_change()
                    for on_change in self._on_change.values():
                        on_change(chat_state)

            self._listeners[chat_state.id] = asyncio.create_task(listen())

    def get_state(self, id: ObjectId) -> ChatState | None:
        if id in self._actions:
            return self._actions[id][0]
        return None

    def add_state(self, chat_state: ChatState):
        self._actions[chat_state.id] = (chat_state, {})

    def add_action(self, chat_state: ChatState, action: Coroutine[Any, Any, Any]):
        action_id = secrets.token_hex(32)
        self._add_listener(chat_state)
        if chat_state.id not in self._actions:
            self._actions[chat_state.id] = (chat_state, {})

        task_action = asyncio.create_task(action)

        async def run_action():
            await task_action
            del self._actions[chat_state.id][1][action_id]

            if len(self._actions[chat_state.id][1]) == 0:
                self._listeners[chat_state.id].cancel()
                del self._listeners[chat_state.id]

        self._actions[chat_state.id][1][action_id] = asyncio.create_task(run_action())

    def add_listener(self, connection_id: str, on_change: Callable[[ChatState], None]):
        self._on_change[connection_id] = on_change

        for chat_state, _ in self._actions.values():
            self._add_listener(chat_state)

    def close(self, connection_id: str):
        del self._on_change[connection_id]

        if len(self._on_change) == 0:
            for listener in self._listeners.values():
                listener.cancel()


class Connections:
    connections: dict[ObjectId, ConnectionManager] = {}

    def get(self, user_id: ObjectId) -> ConnectionManager:
        if user_id not in self.connections:
            self.connections[user_id] = ConnectionManager()

        return self.connections[user_id]
