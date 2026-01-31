"""Templating environment factory for joop.

Contains key implementation for joop templates, providing structure for data
    access inside jinja templates.
If it isn't a joop env, it won't work with joop templating.

Classes:
    EnvironmentFactory:
        A factory class for creating and configuring Jinja2 Environment instances.

        Methods:
            create_environment(**kwargs):
                Creates and configures a Jinja2 Environment instance.
                Registers subcomponent and ata functions.

            _get_joop(ctx: Context) -> dict:
                Retrieves the 'joop' dictionary from the Jinja2 context.

            subcomponent(ctx: Context, subcomponent_name: str) -> Markup:
                Retrieves and marks a subcomponent as safe HTML.

            data(ctx: Context, key: str) -> str:
                Retrieves data associated with a key from the Jinja2 context.

Usage:
    - Use `EnvironmentFactory.create_environment()` to create a Jinja2 Environment.
    - Use `subcomponent` and `data` methods to access joop data and subcomponents within a rendered template.

"""

from jinja2 import Environment as JinjaEnvironment, pass_context
from jinja2.runtime import Context
from markupsafe import Markup

_JOOP_ROOT = 'joop'
_SUBCOMPONENT_ROOT = 'sc'
_DATA_ROOT = 'data'

class EnvironmentFactory:
    """
    A factory class for creating and configuring Jinja2 Environment instances.

    This class provides static methods to create a Jinja2 Environment and to define custom
    functions for interacting with the Jinja2 context, such as retrieving subcomponents
    and data.

    Methods:
        create_environment(**kwargs):
            Creates and configures a Jinja2 Environment instance.

        _get_joop(ctx: Context) -> dict:
            Retrieves the 'joop' dictionary from the Jinja2 context.

        subcomponent(ctx: Context, subcomponent_name: str) -> Markup:
            Retrieves and marks a subcomponent as safe HTML.

        data(ctx: Context, key: str) -> str:
            Retrieves data associated with a key from the Jinja2 context.
    """

    @staticmethod
    def create_environment(**kwargs):
        """Factory method to create and configure a Jinja2 Environment.

        Important: Registers the two main joop functions to the environment:
            'subcomponents' and 'data'.

        Args:
            **kwargs: Arbitrary keyword arguments to configure the Jinja2 Environment.

        Returns:
            JinjaEnvironment: A configured Jinja2 Environment instance.

        Usage Example:
            env = EnvironmentFactory.create_environment(autoescape=True)
        """
        env = JinjaEnvironment(**kwargs)
        env.globals.update({
            'subcomponent': EnvironmentFactory.subcomponent,
            'data': EnvironmentFactory.data,
        })
        return env

    @staticmethod
    def _get_joop(ctx: Context) -> dict:
        """
        Retrieve the 'joop' dictionary from the Jinja2 context.

        Used by both `subcomponent` and `data` functions.
        May seem like a lot of overhead, but it centralizes logic
            and keeps everything in its place.

        Args:
            ctx (Context): The Jinja2 context object.

        Returns:
            dict: The 'joop' dictionary if it exists, otherwise an empty dictionary.
        """
        return ctx.get(_JOOP_ROOT, {})

    @staticmethod
    @pass_context
    def subcomponent(ctx: Context, subcomponent_name: str) -> Markup:
        """
        Retrieve and mark a subcomponent as safe HTML.

        Args:
            ctx (Context): The Jinja2 context object.
            subcomponent_name (str): The name of the subcomponent to retrieve.

        Returns:
            Markup: The safe HTML content of the subcomponent, or an empty string if the subcomponent is not found.

        This function accesses the Jinja2 context to fetch a subcomponent stored under a specific name.
        It ensures that the subcomponent is retrieved safely and marked as safe HTML.
        If the subcomponent does not exist, an empty string is returned.
        """
        _sc_val = EnvironmentFactory._get_joop(ctx).get(_SUBCOMPONENT_ROOT, {}).get(subcomponent_name, "")
        return Markup(_sc_val)
    
    @staticmethod
    @pass_context
    def data(ctx: Context, key: str) -> str:
        """
        Retrieve data associated with a key from the Jinja2 context.

        Args:
            ctx (Context): The Jinja2 context object.
            key (str): The key for the data to be retrieved.

        Returns:
            str: The data associated with the key, or an empty string if not found.

        This function accesses the Jinja2 context to fetch data stored under a specific key.
        It ensures that the data is retrieved safely and returns an empty string if the key
        does not exist in the context.
        """
        _sc_val = EnvironmentFactory._get_joop(ctx).get(_DATA_ROOT, {}).get(key, "")
        return _sc_val
