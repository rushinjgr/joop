"""

This file contains examples for learning, development, and testing of joop.web components.
Included is examples of how to define and implement web components of the most basic kind.

"""

from joop.web import HTMLComponent

class HelloWorld(HTMLComponent):

    # Every HTMLComponent has a template location.
    _template_location = "hello.html"

    # A definition of an inner input class is required.
    class Inputs(HTMLComponent.Inputs):
        # Even if it's empty.
        pass

    # For the inner classes, inherit from the parent class:
    class Data(HTMLComponent.Data):
        pass

        # `from_inputs` must be defined as well.
        @classmethod # Yes, you still have to specify classmethod.
        # Also, it is good to be specific with type hints:
        def from_inputs(cls, inputs : 'HelloWorld.Inputs') -> 'HelloWorld.Data':
            # If you've got a no-op class like this, use:
            return super()._from_inputs(inputs)
    
    # Copy-pasting the above ^^^ to a new component is safe
    
    # Same as inputs, just make an empty class if there are no
    #   child/sub components.
    class SubComponents(HTMLComponent.SubComponents):
        pass

'''
To then render the hello world component:
```
component         = HelloWorld()
component.inputs  = component.Inputs()
# You don't need to do data because of the `from_inputs`.
component.subs    = component.SubComponents()
return component.render()
```
That's it. But why complicate a "hello world" by
requiring empty classes, functions etc.?
A few reasons:
1. We don't optimize for "hello world" because real
    components are unlikely to be this simple, but
    compromise on succintness for the sake of simplicity
    and consistency.
2. joop is a declarative paradigm, and accordingly,
    explicitly declared symbols show the class inheritance.
3. Explicitly declared stubs show you that nothing is there.
4. It facilitates the derivation of more complex components
    from more simple ones (and possibly, vice-versa).
5. A place for everything, and everything in its place.
'''

# Now for a component with dynamic data rendering.

class HelloName(HTMLComponent):
    _template_location = "hello_name.html"  # Adjusted for simplicity

    # Inputs and data are dataclasses via inheritance (there's a bit of trickery).
    class Inputs(HTMLComponent.Inputs):
        first_name: str
        last_name : str
    
    # Inputs is what it sounds like.
    # Data goes to the template to be rendered.
    class Data(HTMLComponent.Data):
# The name of the data fields will be used in the template.
        full_name : str

        @classmethod
        def from_inputs(cls, inputs: "HelloName.Inputs") -> "HelloName.Data":
            res = f"{inputs.first_name} {inputs.last_name}"
            return cls(full_name = res)

    class SubComponents(HTMLComponent.SubComponents):
        pass
'''
To then render the hello name component:
```
component         = HelloName()
component.inputs  = component.Inputs(
                    first_name  = "Justin",
                    last_name   = "Rushin")
component.subs    = res.SubComponents()
return component.render()
```
'''

# Now for an example with subcomponents aka:
#   child components, or nested components.

class HelloSuperComponent(HTMLComponent):
        # Of course, this is our/outer's template. Inner
        #   template isn't specified. It's in the subcomponent.
        _template_location = "hello_supercomponent.html"

        # Empty inputs and data classes follow:
        class Inputs(HTMLComponent.Inputs):
            pass

        class Data(HTMLComponent.Data):

            @classmethod
            def from_inputs(cls, inputs):
                return super()._from_inputs(inputs)
        
        class SubComponents(HTMLComponent.SubComponents):
            # No need to specify a default factory.
            # We use some trickery. Just specify the class
            #   of the child component.
            my_hello: HelloWorld

        def render(self) -> str:
            return super().render()

'''
To render this component with nesting:
```
component           = HelloSuperComponent()
component.inputs    = component.Inputs() # empty inputs
subcomponent        = HelloWorld(parent = component)
subcomponent.inputs = subcomponent.Inputs()
component.subs      = component.SubComponents(
    my_hello = subcomponent
)
component.render()
```
`render` will include subcomponents recursively.
'''

'''
To summarize, a component is made by:
1. Deriving the outer class from the correct class.
2. Defining the fields/properties of the innner classes.
3. Implementing the `from_inputs` function to transform
    input to output.
4. Carrying out any other special implementation necessary.

Of course, this ignores what's done on the template side.
'''
