""" An HTML Component is a joop Component that renders to HTML.

Like many projects, joop achieves this via jinja templating.
There is a specific structure for template variables that joop imposes to meet
its goals of providing a "place for everything and everything in its place."

Classes:
    HTML:
        A base class for managing Jinja2 templates and rendering HTML content.

    HTMLComponent:
        A component class that extends both Component and HTML to provide
        functionality for rendering HTML components with subcomponents and data.

"""

import jinja2
from typing import Optional
from dataclasses import asdict, fields
from joop.web.component import Component
from joop.web.j_env import get_joop_env

class HTML():
    """
    A base class for managing Jinja2 templates and rendering HTML content.

    Its main purpose is to tie behavior to a specific Jinja2 env, especially
        in terms of template location.

    This class provides methods for initializing and managing a Jinja2 environment
    and loading templates for rendering HTML.

    Attributes:
        _template_location (str): The location of the Jinja2 template file.
        _jinja_env (Optional[jinja2.Environment]): The Jinja2 environment used for rendering.

    Methods:
        __init__(j_env: Optional[jinja2.Environment] = None):
            Initializes the HTML class with a Jinja2 environment.

        _get_template() -> jinja2.Template:
            Retrieves the Jinja2 template based on the template location.
    """
    _template_location: None
    _jinja_env: Optional[jinja2.Environment] = None

    def __init__(self, j_env: Optional[jinja2.Environment] = None):
        """
        Initialize the HTML class with a Jinja2 environment.

        Args:
            j_env (Optional[jinja2.Environment]): The Jinja2 environment to use for rendering.

        Raises:
            ValueError: If no Jinja2 environment is provided or available.
        """
        if j_env is not None:
            self._jinja_env = j_env
        elif self._jinja_env is None:
                self._jinja_env = get_joop_env()
        
        if self._jinja_env is None:
            raise ValueError("A Jinja2 environment must be provided either as a class property or during initialization.")

    def _get_template(self) -> jinja2.Template:
        """
        Retrieve the Jinja2 template based on the template location.

        Returns:
            jinja2.Template: The Jinja2 template object.
        """
        _res = self._jinja_env.get_template(self._template_location)
        return _res
    
class HTMLComponent(Component, HTML):
    """
    A component class that extends both Component and HTML to provide functionality
    for rendering HTML components with subcomponents and data.

    This class integrates the base Component class with the HTML class to enable
    dynamic rendering of HTML components using Jinja2 templates.

    Attributes:
        _loaded_template (jinja2.Template): The loaded Jinja2 template for the component.

    Methods:
        __init__(j_env: Optional[jinja2.Environment] = None, parent: Optional[Component] = None):
            Initializes the HTMLComponent with a Jinja2 environment and an optional parent component.

        _load_template():
            Loads the Jinja2 template for the component.

        render(as_subcomponent: bool = False, **kwargs) -> str:
            Renders the component as a string, optionally as a subcomponent.

    Nested Classes:
        SubComponents:
            A class for managing subcomponents of the HTMLComponent.

            Methods:
                get_all -> dict[str, 'Component']:
                    Retrieves all subcomponents as a dictionary.

                render():
                    Renders all subcomponents and stores their HTML output.

                get_rendered() -> dict[str, str]:
                    Returns the rendered HTML output of all subcomponents.
    """

    class SubComponents(Component.SubComponents):
        """
        A class for managing subcomponents of the HTMLComponent.

        Methods:
            get_all -> dict[str, 'Component']:
                Retrieves all subcomponents as a dictionary.

            render():
                Renders all subcomponents and stores their HTML output.

            get_rendered() -> dict[str, str]:
                Returns the rendered HTML output of all subcomponents.
        """

        @property
        def get_all(self) -> dict[str, 'Component']:
            """
            Retrieve all subcomponents as a dictionary.

            Returns:
                dict[str, Component]: A dictionary where keys are subcomponent names
                and values are the subcomponent instances.
            """
            return {field.name: getattr(self, field.name) for field in fields(self)}

        def render(self):
            """
            Render all subcomponents and store their HTML output.

            This method iterates through all subcomponents, renders each one, and
            stores the resulting HTML in a dictionary.
            """
            self._rendered_sc_html = {}
            for _sc_name, _sc_inst in self.get_all.items():
                self._rendered_sc_html[_sc_name] = _sc_inst.render(as_subcomponent = True)

        def get_rendered(self) -> dict[str, str]:
            """
            Return the rendered HTML output of all subcomponents.

            This method ensures that all subcomponents are rendered and returns
            their HTML output as a dictionary.

            Returns:
                dict[str, str]: A dictionary where keys are subcomponent names and
                values are their rendered HTML output.
            """
            self.render()
            return self._rendered_sc_html

    def __init__(self, j_env: Optional[jinja2.Environment] = None, parent: Optional[Component] = None):
        """
        Initialize the HTMLComponent with a Jinja2 environment and an optional parent component.

        Args:
            j_env (Optional[jinja2.Environment]): The Jinja2 environment to use for rendering.
            parent (Optional[Component]): The parent component, if any.
        """
        super().__init__(parent=parent, j_env=j_env)  # Pass both arguments to super()

    _loaded_template: jinja2.Template
    
    def _load_template(self):
        """
        Load the Jinja2 template for the component.

        This method retrieves the template using the _get_template method and
        stores it in the _loaded_template attribute.
        """
        self._loaded_template = self._get_template()

    def render(self, as_subcomponent : bool = False, **kwargs) -> str:
        """
        Render the component as a string, optionally as a subcomponent.

        This method prepares the component for rendering, loads the template,
        and renders the HTML output using the provided data and subcomponents.

        Args:
            as_subcomponent (bool): Whether to render the component as a subcomponent.
            **kwargs: Additional keyword arguments for rendering.

        Returns:
            str: The rendered HTML output.
        """
        if as_subcomponent == True:
            self.inputs = self.Inputs(**kwargs)
        super().render()
        if as_subcomponent == True:
            self.subs = self.SubComponents()
        self._load_template()
        _joop = {
                'sc' : self.subs.get_rendered(),
                'data' : asdict(self.data)
            } 
        print(_joop)
        return self._loaded_template.render(
            joop = _joop
        )

    # render.__isabstractmethod__ = True