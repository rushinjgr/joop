"""Web module.

All functionality related to web-backends, HTML templating, etc. lives here.

Modules:
    component: Define web UI or API components.
    html: Where components get rendered to HTML.
    view: Register components to webservers, set up views routes, etc.

"""

from joop.web.component import Component #, JSONComponent
from joop.web.html import HTML, HTMLComponent
from joop.web.view import View
