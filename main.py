#!/usr/bin/env python

#
# main module for snap microservices framework
#
# 

import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
import argparse
import sys, os
import yaml
import common


HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_DEFAULT_ERRORCODE = 400
HTTP_NOT_IMPLEMENTED = 500

MIMETYPE_JSON = 'application/json'
CONFIG_FILE_ENV_VAR = 'BUTTONIZE_CFG'


class MissingDataStatus():
    def __init__(self, field_name):
        self.message = 'The field "%s" is missing or empty.' % field_name

    def __repr__(self):
        return self.message

    
class MissingInputFieldException(Exception):
    def __init__(self, missing_data_status_errors):
        Exception.__init__(self, "One or more errors or omissions detected in input data: %s" % (','.join(missing_data_status_errors)))

        
class UnregisteredTransformException(Exception):
    def __init__(self, transform_name):
        Exception.__init__(self, 'No transform named "%s" has been registered with the object transform service.' % transform_name)

        
class NullTransformInputDataException(Exception):
    def __init__(self, transform_name):
        Exception.__init__(self, 'A null data table was passed in to the object transform service for type "%s". Please check your HTTP request body or query string.' 
                           % transform_name)


class TransformNotImplementedException(Exception):
    def __init__(self, transform_name):
        Exception.__init__(self, 'transform function %s exists but performs no action. Time to add some code.' % transform_name)


def load_snap_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snap_config_file", metavar='<snap config file>', required=True, nargs=1, help='YAML config file for snap endpoints')

    args = parser.parse_args()
    config_file_path = common.full_path(args.snap_config_file[0])

    return common.read_config_file(config_file_path)
    

def initialize_logging(yaml_config_obj, app):
    app.debug =  yaml_config_obj['globals']['debug']
    logfile_name = yaml_config_obj['globals']['logfile']

    handler = RotatingFileHandler(logfile_name, maxBytes=10000, backupCount=1)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    logging.getLogger('wekzeug').addHandler(handler)


def initialize_services(yaml_config_obj, app):
    service_objects = {}
    for service_object_name in yaml_config_obj['service_objects']:
        config_segment = yaml_config_obj['service_objects'][service_object_name]
        service_object_classname = config_segment['class']
        service_module_name = yaml_config_obj['globals']['service_module']
        parameter_array = config_segment['init_params']

        param_tbl = {}
        for param in parameter_array:
            param_name = param['name']
            param_value = param['value']
            param_tbl[param_name] = param_value

        klass = common.load_class(service_object_classname, service_module_name)
        service_object = klass(app.logger, **param_tbl)
        service_objects[service_object_name] = service_object
        
    return service_objects
    

def setup(app):
    if app.config.get('initialized'):
        return
    yaml_config = load_snap_config() 
    initialize_logging(yaml_config, app)
    service_object_tbl = initialize_services(yaml_config, app)
    
    # load the service objects into the app
    #
    app.config['services'] = common.ServiceObjectRegistry(service_object_tbl) 
    app.config['initialized'] = True
    


from routes import app
setup(app)
    

if __name__ == '__main__':
    '''If we are loading from command line,
    run the Flask app explicitly
    '''
    
    app.run()



