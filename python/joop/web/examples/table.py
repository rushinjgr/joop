"""
This module provides an example implementation of a table component and its integration into a web page.
It demonstrates the usage of the `AlpineTableComponent` for rendering tables and the `View` class for creating web pages.
"""

from joop.web.components import AlpineTableComponent
from joop.web.view import View
from joop.web.html import HTMLComponent
from joop.http.methods import HttpMethod
from joop.web.examples.view import HELLO_DESIG, HELLO_ROOT
from joop.dao import DAO
from pydantic import BaseModel

class Hello_DAO(DAO):
    """
    A Data Access Object (DAO) for handling data related to the `Hello_Model`.

    Attributes:
        Hello_Model (BaseModel): A Pydantic model representing the data structure.
    """

    class Hello_Model(BaseModel):
        """
        A Pydantic model representing a simple data structure with a single field `Desig`.

        Attributes:
            Desig (str): A string field representing a designation.
        """
        Desig : str

    _modeltype = Hello_Model

class MyTableComponent(AlpineTableComponent):
    """
    A custom table component that extends the `AlpineTableComponent`.

    Attributes:
        _row_type (type): Specifies the type of row data to be used in the table.
    """
    _row_type = Hello_DAO

    class Inputs(AlpineTableComponent.Inputs):
        """
        Represents the input data structure for the `MyTableComponent`.
        Extend this class to define specific input fields for the table.
        """
        pass

    class Data(AlpineTableComponent.Data):
        """
        Represents the data structure for the `MyTableComponent`.

        Attributes:
            definition_name (str): The name of the table definition.
        """
        definition_name : str = "myTable"

        @classmethod
        def from_inputs(cls, inputs : 'MyTableComponent.Inputs') -> AlpineTableComponent.Data:
            """
            Create a `Data` instance from the provided inputs.

            Args:
                inputs (MyTableComponent.Inputs): The input data for the table.

            Returns:
                AlpineTableComponent.Data: An instance of the Data class with initialized values.
            """
            return cls(
                rows = [
                    Hello_DAO.from_model(Hello_DAO.Hello_Model(Desig = "Hello")),
                    Hello_DAO.from_model(Hello_DAO.Hello_Model(Desig = "World"))
                ],
                table_headers = cls._get_table_headers()
            )
        
    class SubComponents(AlpineTableComponent.SubComponents):
        """
        Represents subcomponents of the `MyTableComponent`.
        Extend this class to define specific subcomponents.
        """
        pass

class MyTablePage(HTMLComponent):
    """
    A web page component that includes the `MyTableComponent`.

    Attributes:
        _template_location (str): Path to the HTML template for the page.
    """
    _template_location = "table/page.html"

    class Inputs(HTMLComponent.Inputs):
        """
        Represents the input data structure for the `MyTablePage`.
        Extend this class to define specific input fields for the page.
        """
        pass

    class Data(HTMLComponent.Data):
        """
        Represents the data structure for the `MyTablePage`.
        """

        @classmethod
        def from_inputs(cls, inputs : 'MyTablePage.Inputs'):
            """
            Create a `Data` instance from the provided inputs.

            Args:
                inputs (MyTablePage.Inputs): The input data for the page.

            Returns:
                MyTablePage.Data: An instance of the Data class with initialized values.
            """
            return cls()
    
    class SubComponents(HTMLComponent.SubComponents):
        """
        Represents subcomponents of the `MyTablePage`.

        Attributes:
            table (MyTableComponent): An instance of the `MyTableComponent`.
        """
        table: MyTableComponent

        def __init__(self):
            super().__init__()
            self.table = MyTableComponent()

class MyTableWholePage(View):
    """
    A web view that renders the `MyTablePage` component.

    Attributes:
        _component_type (type): Specifies the type of the main component for the view.
    """
    _component_type = MyTablePage

    class Endpoint(View.Endpoint):
        """
        Defines the endpoint for the `MyTableWholePage` view.

        Attributes:
            _url (str): The URL path for the endpoint.
            _name (str): The name of the endpoint.
            _methods (list): The HTTP methods supported by the endpoint.
        """
        _url = HELLO_ROOT + "/table"
        _name = HELLO_DESIG + "_table"
        _methods = [HttpMethod.GET.value]
