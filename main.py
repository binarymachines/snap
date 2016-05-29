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



