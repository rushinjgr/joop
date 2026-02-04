"""

This is an example of how to define Views from components.

"""

from joop.http.methods import HttpMethod
from joop.web.examples.hello import HelloWorld, HelloName
from joop.web.view import View

HELLO_ROOT = "/hello"
HELLO_DESIG = "hello"

class HelloView(View):

    _component_type = HelloWorld

    class Endpoint(View.Endpoint):
        _url = HELLO_ROOT
        _name = HELLO_DESIG
        _methods = [HttpMethod.GET.value]
    
class NameView(View):

    _component_type = HelloName

    class Endpoint(View.Endpoint):
        _url = HELLO_ROOT + "/<string:first_name>/<string:last_name>"
        _name = HELLO_DESIG + "_name"
        _methods = [HttpMethod.GET.value]
