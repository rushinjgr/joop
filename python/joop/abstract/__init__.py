"""
This module provides utilities for abstract behavior.

Classes:
    AbstractMethod: A descriptor to define abstract methods in classes, particularly useful with ABCMeta and dataclasses.

Functions:
    exclude_fields_from_my_init(cls, tgt_fields):
        Modifies a dataclass to exclude specified fields from its `__init__` method.
"""

from typing import List, Any
from dataclasses import field

class AbstractMethod:
    """
    A descriptor for defining abstract methods in classes.

    This class is particularly useful when working with ABCMeta classes and/or dataclasses.
    It allows marking methods as abstract, ensuring that they must be overridden in subclasses.

    Example usage:
        @classmethod
        def _my_abstract_class_method(cls, something: Any):
            raise NotImplementedError("Abstract; not implemented")

        _my_abstract_class_method = AbstractMethod(_my_abstract_class_method)

    Attributes:
        func (callable): The function to be marked as abstract.
        _isabstract (bool): A flag indicating whether the method is abstract.
    """

    def __init__(self, func):
        """
        Initialize the AbstractMethod descriptor.

        Args:
            func (callable): The function to be marked as abstract.
        """
        self.func = func
        self._isabstract = True  # Custom flag to mark as abstract

    def __get__(self, instance, owner):
        """
        Bind the method to the class or instance.

        Raises:
            NotImplementedError: If the method is abstract and not overridden.

        Returns:
            callable: The bound method.
        """
        if self._isabstract:
            raise NotImplementedError(f"The method {self.func.__name__} is abstract and must be overridden.")
        return self.func.__get__(instance, owner)

    @property
    def __isabstractmethod__(self):
        """
        Check if the method is abstract.

        Returns:
            bool: True if the method is abstract, False otherwise.
        """
        return self._isabstract

    @__isabstractmethod__.setter
    def __isabstractmethod__(self, value):
        """
        Set the abstract status of the method.

        Args:
            value (bool): The new abstract status.
        """
        self._isabstract = value

def exclude_fields_from_my_init(cls, tgt_fields: List[str]):
    """
    Exclude specified fields from the `__init__` method of a dataclass.

    This function is intended to be called in the `__init_subclass__` class method
    of a dataclass. It ensures that the fields with names in the provided list
    are marked as non-init fields.

    Args:
        cls (type): The dataclass to modify.
        tgt_fields (List[str]): A list of field names to exclude from the `__init__` method.

    """
    for _field_name in tgt_fields:
        current_value = getattr(cls, _field_name, None)
        if _field_name not in cls.__annotations__:
            cls.__annotations__[_field_name] = Any
        setattr(cls, _field_name, field(init=False, default=current_value))
