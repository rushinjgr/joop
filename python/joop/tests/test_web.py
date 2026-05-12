"""Unit tests for joop web components.

We're testing both components, their templates, and the rendering here.
"""

import json
from joop.web import HTMLComponent, JSONComponent
import unittest
from dataclasses import is_dataclass, dataclass, asdict
from joop.tests.test_templater import environment
from joop.web.examples.hello import (
    HelloWorld, HelloName, HelloSuperComponent
)

# Create our classes for the test and
#   specify the environment via multiple inheritance:

class BaseTestHTMLComponent(HTMLComponent):
        _jinja_env = environment

class MyHello(HelloWorld,
BaseTestHTMLComponent): pass

class MyHelloName(HelloName,
BaseTestHTMLComponent): pass

class MyHelloSuper(HelloSuperComponent,
BaseTestHTMLComponent):     pass


class ExampleJSONComponent(JSONComponent):

    class Inputs(JSONComponent.Inputs):
        message: str

    class Data(JSONComponent.Data):
        message: str

        @classmethod
        def from_inputs(
                cls,
                inputs: "ExampleJSONComponent.Inputs",
                ) -> "ExampleJSONComponent.Data":
            return cls(message=inputs.message)

    class SubComponents(JSONComponent.SubComponents):
        pass


class ExampleJSONSuperComponent(JSONComponent):

    class Inputs(JSONComponent.Inputs):
        message: str

    class Data(JSONComponent.Data):
        message: str

        @classmethod
        def from_inputs(
                cls,
                inputs: "ExampleJSONSuperComponent.Inputs",
                ) -> "ExampleJSONSuperComponent.Data":
            return cls(message=inputs.message)

    class SubComponents(JSONComponent.SubComponents):
        child: ExampleJSONComponent

class TestHTMLComponent(unittest.TestCase):
    
    def _setup_hello(self):
        self.hello = MyHello()
        self.hello.inputs = MyHello.Inputs()
        self.hello.subs = MyHello.SubComponents()
    
    def _setup_name(self):
        self.hello_name = MyHelloName()
        self.hello_name.inputs = MyHelloName.Inputs(first_name = "Justin",
                                                  last_name = "Rushin")
        self.hello_name.subs = MyHelloName.SubComponents()

    def _setup_super(self):
        self.hello_super = MyHelloSuper()
        self.hello_super.inputs = MyHelloSuper.Inputs()

    def setUp(self):
        # Configure the Jinja2 environment with a FileSystemLoader
        self._setup_hello()
        self._setup_name()
        self._setup_super()

    def test_000_type_check(self):
        # here, we are verifying that our custom abstract code works
        assert is_dataclass(self.hello.inputs) 

    def test_001_hello_world(self):
        hello_html = self.hello.render()
        assert hello_html == "<p>Hello, World!</p>"
    
    def test_002_hello_name(self):
        hello_name_html = self.hello_name.render()
        _tgt_html = """<p>Hello, Justin Rushin!</p>"""
        assert hello_name_html == _tgt_html

    def test_003_hello_subcomponent(self):
        _hello = MyHello(parent=self.hello_super)
        _hello.inputs = MyHello.Inputs()
        _hello.subs = MyHello.SubComponents()
        self.hello_super.subs = MyHelloSuper.SubComponents(
            my_hello = _hello
        )
        assert is_dataclass(self.hello_super.subs)
        hello_super_html = self.hello_super.render()
        _tgt_html = """<p>I'm a supercomponent! And I say:</p>\n<p>Hello, World!</p>"""
        assert hello_super_html == _tgt_html


class TestJSONComponent(unittest.TestCase):

    def test_000_json_component_renders_json(self):
        component = ExampleJSONComponent()
        component.inputs = component.Inputs(message="Hello JSON")
        component.subs = component.SubComponents()

        rendered_json = component.render()

        self.assertEqual(
            json.loads(rendered_json),
            {
                "sc": {},
                "data": {"message": "Hello JSON"},
            },
        )

    def test_001_json_component_render_data_supports_subcomponent_kwargs(self):
        component = ExampleJSONComponent()

        rendered_data = component.render_data(
            as_subcomponent=True,
            message="Hello Subcomponent",
        )

        self.assertEqual(
            rendered_data,
            {
                "sc": {},
                "data": {"message": "Hello Subcomponent"},
            },
        )

    def test_002_json_component_renders_nested_subcomponents(self):
        component = ExampleJSONSuperComponent()
        component.inputs = component.Inputs(message="Parent")
        child = ExampleJSONComponent(parent=component)
        child.inputs = child.Inputs(message="Child")
        child.subs = child.SubComponents()
        component.subs = component.SubComponents(child=child)

        rendered_json = component.render()

        self.assertEqual(
            json.loads(rendered_json),
            {
                "sc": {
                    "child": {
                        "sc": {},
                        "data": {"message": "Child"},
                    }
                },
                "data": {"message": "Parent"},
            },
        )
