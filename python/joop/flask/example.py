"""

This is the default place to turn example or other View definitions into
    flask-specific views.
"""

from joop.web.examples.view import (
    NameView, HelloView
)

from joop.web.examples.table import MyTableView

from joop.flask.flask_view import FlaskView

class FlaskHello(HelloView, FlaskView): pass

class FlaskName(NameView, FlaskView): pass

class FlaskTable(MyTableView, FlaskView): pass