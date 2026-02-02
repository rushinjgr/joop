"""HTTP Methods Enumeration Module.

joop uses its own HTTP method enum implementation for compatibility purposes with
older versions of python, to provide a standardized way to
represent and describe HTTP methods.

Classes:
    HttpMethod:
        An enumeration of HTTP methods, each with a corresponding description.

        Methods:
            description() -> str:
                Returns a description of the HTTP method.

Usage:
    - Use `HttpMethod` to refer to HTTP methods in a type-safe manner.
    - Call the `description` method on an `HttpMethod` instance to get its description.

"""

from enum import Enum

class HttpMethod(str, Enum):  # Changed from StrEnum to str + Enum for Python 3.10 compatibility
    """Enumeration of HTTP methods with their descriptions."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    TRACE = "TRACE"
    CONNECT = "CONNECT"

    def description(self) -> str:
        """Return a description of the HTTP method."""
        descriptions = {
            "GET": "Retrieve data from the server.",
            "POST": "Submit data to the server.",
            "PUT": "Update or create a resource on the server.",
            "DELETE": "Delete a resource on the server.",
            "PATCH": "Apply partial modifications to a resource.",
            "OPTIONS": "Describe the communication options for the target resource.",
            "HEAD": "Retrieve metadata about the resource without the body.",
            "TRACE": "Perform a message loop-back test along the path to the target resource.",
            "CONNECT": "Establish a tunnel to the server identified by the target resource."
        }
        return descriptions[self.value]