"""
Useful components for web development.
It includes a base class `AlpineTableComponent` for generating AlpineJS-powered
    tables based on Pydantic or SQLModel models.
The module also defines data access object (DAO) classes for handling row data.
"""

from joop.web.html import HTMLComponent
from joop.dao import DAO
import typing

class MetaRowDAO(DAO):
    """
    Implementation pending.
    A base Data Access Object (DAO) class for handling row data.
    This class can be extended to implement specific data access logic.
    """
    pass

class RowDAO(MetaRowDAO):
    """
    Implementation pending.
    A concrete implementation of `MetaRowDAO` for handling generic row data.
    """
    pass

class SQLRowDAO(MetaRowDAO):
    """
    Implementation pending.
    A concrete implementation of `MetaRowDAO` for handling SQL-based row data.
    """
    pass

'''
A common base component to allow for ready-made,
AlpineJS powered
tables based on Pydantic or SQLModel models.
'''
class AlpineTableComponent(HTMLComponent):
    """
    A reusable component for rendering tables using Alpine.js and HTML templates.

    Attributes:
        _template_location (str): Path to the HTML template for the table.
        _use_prefix_template (bool): Determines whether to use a prefixed template directory.
        _row_type (typing.Type[MetaRowDAO]): Specifies the type of row data to be used in the table.
    """
    _template_location = "table/alp_table.html"
    _use_prefix_template = False
    _row_type: typing.Type[MetaRowDAO]

    class Inputs(HTMLComponent.Inputs):
        """
        Represents the input data structure for the `AlpineTableComponent`.
        Extend this class to define specific input fields for the table.
        """
        pass

    class Data(HTMLComponent.Data):
        """
        Represents the data structure for the `AlpineTableComponent`.

        Attributes:
            rows (typing.Iterable[MetaRowDAO]): The rows of data to be displayed in the table.
            table_headers (typing.Any): The headers of the table, derived from the row type.
            _row_type: The type of row data used in the table.
        """
        rows : typing.Iterable[MetaRowDAO]
        table_headers: typing.Any
        _row_type = None

        @classmethod
        def _get_table_headers(cls):
            """
            Retrieve the table headers based on the fields of the row type's model.

            Returns:
                list: A list of field names for the table headers.
            """
            return cls._row_type.get_model_fields()

        @classmethod
        def from_inputs(cls,
                        inputs : 'AlpineTableComponent.Inputs',
                        ) -> 'AlpineTableComponent.Data':
            """
            Create a `Data` instance from the provided inputs.

            Args:
                inputs (AlpineTableComponent.Inputs): The input data for the table.

            Returns:
                AlpineTableComponent.Data: An instance of the Data class with initialized values.
            """
            return cls(rows = [],
                       table_headers = cls._get_table_headers())

    def _process_inputs(self, **kwargs):
        """
        Process the input data and set the row type for the table.

        Args:
            **kwargs: Additional keyword arguments for processing inputs.

        Returns:
            Any: The processed input data.
        """
        self.Data._row_type = self._row_type
        return super()._process_inputs(**kwargs)
    
    class SubComponents(HTMLComponent.SubComponents):
        """
        Represents subcomponents of the `AlpineTableComponent`.
        Extend this class to define specific subcomponents.
        """
        pass
