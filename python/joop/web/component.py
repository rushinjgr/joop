"""

Components are programmatic representations of data or UI elements, designed to be rendered dynamically,
    in the context of a web server.
A highly abstract class, the purpose of it is to provide a standard way to define inputs, outputs,
    and the transformations needed to render them. Components are the backbone of joop.web.

Classes:
    Component:
        The base class for all components, providing a structure for inputs, data, and subcomponents.

    JSONComponent:
        A specialized component for handling JSON data. Implementation pending.

"""

from typing import Optional
from dataclasses import dataclass, fields
from abc import ABCMeta

from joop.abstract import AbstractMethod

class Component(metaclass=ABCMeta):
    '''
    Base class for programmatically rendering data or UI elements.

    This class provides a structure for defining inputs, data, and subcomponents,
    and includes methods for processing inputs and rendering components.

    Attributes:
        inputs (Inputs): The input data for the component.
        data (Data): The processed data for the component.
        subs (SubComponents): The subcomponents of the component.

    Methods:
        _process_inputs():
            Processes the inputs to generate the component's data.

        render() -> str:
            Abstract method to render the component as a string.
    '''

    class Inputs(metaclass=ABCMeta):
        """Abstract base class for defining the input data structure of a component."""
        pass

    Inputs = dataclass(Inputs)

    class _Data(metaclass=ABCMeta):
        """Abstract base class for defining the internal data structure of a component."""
        pass

    _Data = dataclass(_Data)

    class Data(_Data):
        """
        Class for defining the processed data of a component.

        Methods:
            _from_inputs(inputs: Component.Inputs) -> Component.Data:
                Creates a Data instance from the given Inputs.

            from_inputs(inputs: Component.Inputs) -> Component.Data:
                Abstract method to create a Data instance from the given Inputs.
        """

        @classmethod
        def _from_inputs(cls, inputs: 'Component.Inputs') -> 'Component.Data':
            """
            Create a Data instance from the given Inputs.

            Args:
                inputs (Component.Inputs): The input data for the component.

            Returns:
                Component.Data: A new Data instance.
            """
            return cls()

        @classmethod
        def from_inputs(cls, inputs: 'Component.Inputs') -> 'Component.Data':
            """
            Abstract method to create a Data instance from the given Inputs.

            Args:
                inputs (Component.Inputs): The input data for the component.

            Returns:
                Component.Data: A new Data instance.
            """
            return Component.Data() # pragma: no cover

        from_inputs = AbstractMethod(from_inputs)

    class SubComponents(metaclass=ABCMeta):
        """Abstract base class for defining the subcomponents of a component."""
        pass

    SubComponents = dataclass(SubComponents)

    inputs: Inputs
    data: Data
    subs: SubComponents

    def __init__(self, parent: Optional['Component'] = None, *args, **kwargs):
        """
        Initialize a Component instance.

        Args:
            parent (Optional[Component]): The parent component, if any.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)  # Pass additional arguments to the next class in the MRO
        if parent is not None:
            self._parent = parent

    def _process_inputs(self):
        """
        Process the inputs to generate the component's data.

        This method uses the `from_inputs` method of the Data class to create a
        Data instance from the component's inputs.
        """
        self.data = self.Data.from_inputs(self.inputs)

    def render(self) -> str:
        """
        Abstract method to render the component as a string.

        This method processes the inputs and generates the component's data before
        rendering it as a string. Subclasses must implement this method.

        Returns:
            str: The rendered component as a string.
        """
        self._process_inputs()

    render.__isabstractmethod__ = True

    def __init_subclass__(cls, **kwargs):
        """
        Initialize a subclass of Component.

        This method ensures that the Data, Inputs, and SubComponents classes of the
        subclass are decorated as dataclasses.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init_subclass__(**kwargs)
        cls.Data = dataclass(cls.Data)
        cls.Inputs = dataclass(cls.Inputs)
        cls.SubComponents = dataclass(cls.SubComponents)

class JSONComponent(Component):
    """
    A specialized component for handling JSON data.

    Inherits:
        Component: The base Component class.
    """
    pass
