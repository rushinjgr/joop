"""Environment management module for joop.

Important: The main purpose of this module is to be an interface for the jinja environment proxy
    contained within joop for cross platform purposes (ex. run with or without flask.)

This module provides functions to set and get the global templating environment for the joop instance.

Variables:
    joop_env:
        A global variable to store the current templating environment.

Functions:
    set_joop_env(value):
        Sets the global templating environment to the provided value.
        
        Args:
            value: The new environment to set as the global environment.

    get_joop_env():
        Retrieves the current global templating environment.
        
        Returns:
            The current global templating environment.

Usage:
    - Use `set_joop_env(value)` to set the global environment.
    - Use `get_joop_env()` to retrieve the current global environment.

"""

joop_env = None

def set_joop_env(value):
    global joop_env
    joop_env = value

def get_joop_env():
    global joop_env
    return(joop_env)