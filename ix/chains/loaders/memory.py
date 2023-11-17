import logging
from abc import ABC
from functools import singledispatch
from typing import Dict, Any, Union, Type, Tuple, List

from pydantic.v1.fields import ModelField

from ix.chains.callbacks import IxHandler
from langchain.memory import CombinedMemory
from langchain.schema import BaseMemory, BaseChatMessageHistory
from pydantic import BaseModel

from ix.chains.loaders.core import load_node, IxContext
from ix.chains.models import ChainNode
from ix.utils.importlib import import_class
from ix.utils.pydantic import get_model_fields

logger = logging.getLogger(__name__)


# config options for memory classes that do not have Ix specific options
MEMORY_CLASSES = {}


def get_memory_option(cls: Type[BaseModel], name: str, default: Any):
    """Get a memory config value from a class or default"""

    if issubclass(cls, BaseModel) and name in get_model_fields(cls):
        # support for pydantic models
        return get_model_fields(cls)[name].default
    elif issubclass(cls, ABC) and hasattr(cls, "__fields__"):
        # support for abstract classes
        # Pydantic v1/v2 compat, some BaseModels will still fall into this category
        # need to check for ModelField for that case.
        field = cls.__fields__.get(name, default)
        return field.default if isinstance(field, ModelField) else field
    elif hasattr(cls, name):
        # support for regular classes
        return getattr(cls, name)
    elif cls in MEMORY_CLASSES:
        # fallback to separate config
        return MEMORY_CLASSES[cls].get(name, default)
    return default


@singledispatch
def load_memory_config(
    node: ChainNode,
    context: IxContext,
) -> BaseMemory:
    """Load a memory instance using a config"""
    memory_class = import_class(node.class_path)
    logger.debug(f"loading memory class={node.class_path} node={node.id}")
    memory_config = node.config.copy() if node.config else {}

    # load session_id if scope is supported
    supports_session = get_memory_option(memory_class, "supports_session", False)
    if supports_session is True:
        session_id, session_id_key = get_memory_session(
            memory_config, context, memory_class
        )
        memory_config[session_id_key] = session_id

    return memory_config


def load_chat_memory_backend_config(node: ChainNode, ix_handler: IxHandler):
    backend_class = import_class(node.class_path)
    logger.debug(f"loading BaseChatMessageHistory class={backend_class} config={node}")
    backend_config = node.config.copy()

    # always add scope to chat message backend
    session_id, session_id_key = get_memory_session(
        backend_config, ix_handler, backend_class
    )
    logger.debug(
        f"load_chat_memory_backend session_id={session_id} session_id_key={session_id_key}"
    )
    backend_config[session_id_key] = session_id

    return backend_config


def load_memory_property(node_group: List[ChainNode], context: IxContext) -> BaseMemory:
    """
    Load memories from a list of configs and merge in to a CombinedMemory instance.
    """
    logger.debug(f"Combining memory classes config={node_group}")

    if len(node_group) == 1:
        # no need to combine
        return load_node(node_group[0], context)

    # auto-merge into CombinedMemory
    return CombinedMemory(memories=[load_node(node, context) for node in node_group])


def get_memory_session(
    config: Dict[str, Any],
    context: IxContext,
    cls: Union[BaseMemory, BaseChatMessageHistory],
) -> Tuple[str, str]:
    """
    Parse the session scope from the given configuration and callback manager.

    This function retrieves the scope from the configuration, verifies if the scope
    is supported by the given class (cls), and then fetches the corresponding identifier
    from the callback manager based on the scope. It then constructs the session id
    by appending the session id base, scope, and scope id.

    Parameters:
    - config (Dict[str, Any]): The configuration dictionary. Config options include:
      * "scope" (str): The scope of the interaction. Supported scopes are: "chat", "agent", "task", and "user".
      * "prefix" (str): The base string for the session id. Default is an empty string.
      * "key" (str): The key name for the session id in the return tuple. Default is "session_id".

    - callback_manager (IxCallbackManager): The callback manager object which stores identifiers
      for different scopes.

    - cls (Union[BaseMemory, BaseChatMessageHistory]): Class object that supports the required scope.

    Returns:
    - Tuple[str, str]: A tuple containing the session id and session id key.

    Raises:
    - ValueError: If the given scope is not recognized.

    Example:
    config = {
      "scope": "chat",
      "prefix": "prefix_unique_to_chat_scope",
      "key": "session_id"
    }
    session_id, session_id_key = get_memory_session(config, callback_manager, BaseChatMessageHistory)
    """

    # fetch scope
    scope = config.pop("session_scope", "chat")
    if scope in {"", None}:
        scope = "chat"
    if supported_scopes := get_memory_option(cls, "supported_scopes", False):
        assert scope in supported_scopes

    # load session_id from context based on scope
    if scope == "chat":
        scope_id = context.chat_id
    elif scope == "agent":
        scope_id = context.agent.id
    elif scope == "task":
        scope_id = context.task.id
    elif scope == "user":
        scope_id = context.user_id
    else:
        raise ValueError(f"unknown scope={scope}")

    if prefix := config.pop("session_prefix", None):
        session_id = f"{prefix}_{scope}_{scope_id}"
    else:
        session_id = f"{scope}_{scope_id}"

    key = config.pop("session_key", "session_id")
    return session_id, key
