#!/usr/bin/env python

import re

DEFAULT_CONFIG_FILENAME = 'snap.conf'
RESERVED_ROUTES = ['smp', 'api']
ROUTE_VARIABLE_REGEX = re.compile(r'<([a-zA-Z_-]+):([a-zA-Z_-]+)>')


BAD_ROUTE_VAR_PROMPT = '''
It looks like you are attempting to specify a variable in this route.\n
To specify a route variable, use the form <datatype:routevar>.\n
If "datatype" is not one of [int, string, float, path],\n 
you must register a custom converter for your datatype,\n
otherwise Snap will fail to process the URL correctly at runtime.\n'''


BASIC_ROUTE_VAR_REGEX = re.compile(r'<\S+>')

DEFAULT_MIMETYPE = 'application/json'

VALID_FUNCTION_NAME_RX = re.compile(r'^(?![0-9])((?!-).)*$')
