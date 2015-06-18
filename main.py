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
from common import ServiceObjectRegistry




def read_init_file(initfileName):
    '''Load a YAML initfile by name, returning the dictionary of its contents

    '''
    config = None
    with open(initfileName, 'r') as f:
        config = yaml.load(f) 
    return config   



def load_snap_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snap_config_file", metavar='<snap config file>', required=True, nargs=1, help='YAML config file for snap endpoint')

    args = parser.parse_args()
    config_filename = args.snap_config_file[0]

    config_file_path = None
    if config_filename.startswith(os.path.sep):
        config_file_path = config_filename
    else:
        config_file_path = os.path.join(os.getcwd(), config_filename)
    
    return read_init_file(config_file_path)
    


def initialize_logging(yaml_config_obj, app):
    app.debug =  yaml_config_obj['globals']['debug']
    logfile_name = yaml_config_obj['globals']['logfile']

    handler = RotatingFileHandler(logfile_name, maxBytes=10000, backupCount=1)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    logging.getLogger('wekzeug').addHandler(handler)



def load_service_object_class(class_name, module_name):
    module = __import__(module_name)    
    return getattr(module, class_name)

    


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

        klass = load_service_object_class(service_object_classname, service_module_name)
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
    app.config['services'] = ServiceObjectRegistry(service_object_tbl) 
    app.config['initialized'] = True
    



from routes import app
setup(app)
    

if __name__ == '__main__':
    '''If we are loading from command line,
    run the Flask app explicitly
    '''
    
    app.run()



