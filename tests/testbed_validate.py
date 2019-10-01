#!/usr/bin/env python


def validate_json_field(field):    
    if field.__class__.__name__ != 'dict':
        raise Exception('a field specified as "json" must be a dictionary.')
    return True