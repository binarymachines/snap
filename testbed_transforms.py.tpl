#!/usr/bin/env python

 
from snap import snap
from snap import core
import json
from snap.loggers import transform_logger as log


def ping_func(input_data, service_objects, **kwargs):
    return core.TransformStatus(json.dumps({'message': 'pong'}))

def post_target_func(input_data, service_objects, **kwargs):
    return core.TransformStatus(json.dumps(input_data))