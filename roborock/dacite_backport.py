from dataclasses import is_dataclass
from typing import TypeVar, Type, Optional, get_type_hints, Any, Collection, MutableMapping, Union

from dacite.config import Config
from dacite.data import Data
from dacite.dataclasses import (
    get_default_value_for_field,
    get_fields,
)
from dacite.types import (
    is_generic_collection,
    extract_generic,
    is_optional,
    is_subclass, is_generic,
)

T = TypeVar("T")

from collections.abc import Mapping


def is_union(type_: Type) -> bool:
    if is_generic(type_) and type_.__origin__ == Union:
        return True

    from types import UnionType  # type: ignore

    return isinstance(type_, UnionType)


def is_instance(value: Any, type_: Type) -> bool:
    try:
        # As described in PEP 484 - section: "The numeric tower"
        if (type_ in [float, complex] and isinstance(value, (int, float))) or isinstance(value, type_):
            return True
    except TypeError:
        pass
    if is_generic_collection(type_):
        return all(is_instance(item, extract_generic(type_, defaults=(Any,))[0]) for item in value)
    return False


def backport_from_dict(data_class: Type[T], data: Data, config: Optional[Config] = None) -> T:
    """Create a data class instance from a dictionary.

    :param data_class: a data class type
    :param data: a dictionary of a input data
    :param config: a configuration of the creation process
    :return: an instance of a data class
    """
    init_values: MutableMapping[str, Any] = {}
    config = config or Config()
    data_class_hints = get_type_hints(data_class, localns=None)
    data_class_fields = get_fields(data_class)
    for field in data_class_fields:
        field_type = data_class_hints[field.name]
        if field.name in data:
            field_data = data[field.name]
            value = _build_value(type_=field_type, data=field_data, config=config)
        else:
            value = get_default_value_for_field(field)
        if field.init:
            init_values[field.name] = value
    instance = data_class(**init_values)
    return instance


def _build_value(type_: Type, data: Any, config: Config) -> Any:
    if is_optional(type_) and data is None:
        return data
    if is_union(type_):
        data = _build_value_for_union(union=type_, data=data, config=config)
    elif is_generic_collection(type_):
        data = _build_value_for_collection(collection=type_, data=data, config=config)
    elif is_dataclass(type_) and isinstance(data, Mapping):
        data = backport_from_dict(data_class=type_, data=data, config=config)
    for cast_type in config.cast:
        if is_subclass(type_, cast_type):
            data = type_(data)
            break
    return data


def _build_value_for_union(union: Type, data: Any, config: Config) -> Any:
    types = extract_generic(union)
    if is_optional(union) and len(types) == 2:
        return _build_value(type_=types[0], data=data, config=config)
    for inner_type in types:
        value = _build_value(type_=inner_type, data=data, config=config)
        if is_instance(value, inner_type):
            return value


def _build_value_for_collection(collection: Type, data: Any, config: Config) -> Any:
    data_type = data.__class__
    if isinstance(data, Collection) and is_subclass(collection, Collection):
        item_type = extract_generic(collection, defaults=(Any,))[0]
        return data_type(_build_value(type_=item_type, data=item, config=config) for item in data)
