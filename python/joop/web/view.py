"""

Views are how components are integrated with webservers. The view (or route) is defined
    and established by this class.

Classes:
    View:
        The base class for defining and managing views in the joop project.

"""

from typing import List, Callable, Type

from joop.abstract import AbstractMethod
from joop.http.methods import HttpMethod
from joop.web.component import Component

class View():
    """
    The base class for defining and managing views in the joop project.

    This class provides methods for rendering components, managing inputs and
    subcomponents, and integrating views with web frameworks.

    Attributes:
        _component_type (Type[Component]):
            The type of the component associated with the view.

        _args_to_inputs (bool):
            Determines whether to automatically map arguments to component inputs.

        _get_default_subs (bool):
            Determines whether to automatically retrieve default subcomponents.

        _as_response (bool):
            Determines whether the view should render a response instead of a component.

    Methods:
        _get_inputs(**kwargs):
            Retrieves the inputs for the component based on the provided keyword arguments.

        _get_subs(**kwargs):
            Retrieves the default subcomponents for the component.

        render(**kwargs):
            Renders the component and returns the rendered output as a string.

        _add_to_app(app: object, view_func: Callable):
            Abstract method to add the view to a web application.

        add_to_app(app: object):
            Adds the view to a web application with the specified configuration.

        _get_jinja_env():
            Abstract method to retrieve the Jinja2 environment.

        get_jinja_env():
            Retrieves the Jinja2 environment by calling the abstract method.
    """

    _component_type : Type[Component]

    class Endpoint():
        _url: str
        _name : str
        _methods : List[HttpMethod]

    _args_to_inputs : bool = True
    _get_default_subs : bool = True

    '''
    aliases might be added later
    _arg_aliases : dict = {} # aliases might be added later

    @classmethod
    def _process_kwargs_aliases(cls, **kwargs):
        # Rename the keys in kwargs based on the _arg_aliases mapping
        for old_key, new_key in cls._arg_aliases.items():
            if kwargs.get(old_key) is not None:
                if new_key not in kwargs:
                    kwargs[new_key] = kwargs[old_key]
                    del(kwargs[old_key])
                else:
                    raise KeyError(f"Key conflict: '{new_key}' already exists in kwargs.")
    '''

    @classmethod
    def _get_inputs(cls, **kwargs):
        """
        Retrieve the inputs for the component based on the provided keyword arguments.

        Args:
            **kwargs: Keyword arguments to be mapped to the component's inputs.

        Returns:
            Component.Inputs: The inputs for the component, or None if `_args_to_inputs` is False.
        """
        _res = None
        if cls._args_to_inputs == True:
            _res = cls._component_type.Inputs(**kwargs)
            # cls._process_kwargs_aliases(**kwargs)
        return _res
    
    @classmethod
    def _get_subs(cls, **kwargs):
        """
        Retrieve the default subcomponents for the component.

        Args:
            **kwargs: Keyword arguments (not used in the default implementation).

        Returns:
            Component.SubComponents: The default subcomponents for the component, or None if `_get_default_subs` is False.
        """
        _res = None
        if cls._get_default_subs == True:
            _res = cls._component_type.SubComponents()
        return _res


    @classmethod
    def render(cls, **kwargs):
        """
        Render the component and return the rendered output as a string.

        Args:
            **kwargs: Keyword arguments to be passed to the component's inputs and subcomponents.

        Returns:
            str: The rendered output of the component.
        """
        _component = cls._component_type()
        _component.inputs = cls._get_inputs(**kwargs)
        _component.subs = cls._get_subs()
        return _component.render()

    _as_response : bool = False

    ''' To be implemented. For cases where specific response rendering logic is needed.
    @classmethod
    def render_response(cls, instance : 'View' = None, **kwargs):
        if cls._template_name is None:
            raise NotImplementedError("Abstract; not implemented")
        
        if instance is None:
            instance = cls(req)
        
        rendered = cls.render_template(instance= instance, **kwargs)
        return instance._site.make_response(rendered)
    '''
    
    @classmethod
    def _add_to_app(cls, app : object, view_func : Callable):
        """
        Abstract method to add the view to a web application.

        Args:
            app (object): The web application instance.
            view_func (Callable): The view function to associate with the application.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Abstract; not implemented")
    
    _add_to_app = AbstractMethod(_add_to_app)
    
    @classmethod
    def add_to_app(cls, app : object):
        """
        Add the view to a web application with the specified configuration.

        This method validates the view's configuration and registers it with the
        web application using the `_add_to_app` method.

        Args:
            app (object): The web application instance.

        Raises:
            NotImplementedError: If the view's configuration is incomplete or invalid.
        """
        if (cls.Endpoint._url is None or
            cls.Endpoint._name is None or
            cls.Endpoint._methods is None or
            cls._component_type is None):
            raise NotImplementedError("Abstract; not implemented")

        view_func = cls.render
        if cls._as_response == True:
            view_func = cls.render_response

        cls._add_to_app(app, view_func)

    @classmethod
    def _get_jinja_env(cls):
        """
        Abstract method to retrieve the Jinja2 environment.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Abstract; not implemented")
    
    _get_jinja_env = AbstractMethod(_get_jinja_env)

    @classmethod
    def get_jinja_env(cls):
        """
        Retrieve the Jinja2 environment by calling the abstract method.

        Returns:
            jinja2.Environment: The Jinja2 environment associated with the view.
        """
        return cls._get_jinja_env()
