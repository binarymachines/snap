#!/usr/bin/env python

import os, sys
import argparse
import yaml
import jinja2
import common

default_config_filename = 'snap.conf'


class MissingHandlerFunctionException(Exception):
    def __init__(self, handler_name, handler_module_name):
        Exception.__init__(self, 'No function "%s" present in python module "%s.py"' % (handler_name, handler_module_name))


class NoSuchHandlerException(Exception):
    def __init__(self, handler_name):
        Exception.__init__(self, 'No handler registered under the alias "%s".' % handler_name)




class Route(object):
    def __init__(self, name, urlPath, method_string, handler_name):
        self.name = name
        self.path = urlPath
        self._methods = [method_name.strip() for method_name in method_string.split(',')]
        self.handler_name = handler_name


    @property
    def methods(self):
        method_list = ["'%s'" % m for m in self._methods]
        return ', '.join(method_list)


    def __repr__(self):
        full_path = ''.join(['http://<base_url>'.rstrip('/'), self.path])        
        return '%s %s, handler: %s' % (self.methods, full_path, self.handler)
        



class RouteHandlerRef():
    def __init__(self, function_name):
        self.function_name = function_name


    def __repr__(self):
        return 'handler function "%s" ' % (self.function_name)
        

        
class RouteGenerator():
    def __init__(self, yaml_config):
        self.route_table = self.generate_routes(yaml_config)        
        self.handler_module_name = yaml_config['globals']['handler_module']
        self.handler_table = self.load_handler_refs(self.handler_module_name, yaml_config)


    def load_handler_refs(self, handler_module_name, yaml_config):

        handler_module = __import__(self.handler_module_name)
        handler_module_functions = dir(handler_module)
        
        refs = {}
        yaml_handlers_segment = yaml_config['handlers']
        for handler_alias in yaml_handlers_segment:
            handler_function_name = yaml_handlers_segment[handler_alias]['function']
            
            if handler_function_name not in handler_module_functions:
                raise MissingHandlerFunctionException(handler_function_name, handler_module_name)
            
            new_ref = RouteHandlerRef(handler_function_name)
            refs[handler_alias] = new_ref

        return refs


    def read_environment_value(self, val_name):
        '''Read a value (i.e. from a YAML file) in the standard format
        (leading dollar sign), indicating that the value resides in an
        environment variable
        '''
        return val_name[1:]

    
    def generate_routes(self, yaml_config):
        routes = {}
        yaml_segment =  yaml_config['routes']
        for route_name in yaml_segment:
            path = yaml_segment[route_name]['path']
            methods = yaml_segment[route_name]['method'].upper()
            handler_name = yaml_segment[route_name]['handler']
            
            new_route = Route(route_name, path, methods, handler_name)
            routes[route_name] = new_route
            
        return routes

    def function_name_for_handler(self, handler_name):
        handler_ref = self.handler_table.get(handler_name)
        if not handler_ref:
            raise NoSuchHandlerException(handler_name)

        return handler_ref.function_name


    @property
    def routes(self):
        return self.route_table.values()
        

def main(argv):
    parser = argparse.ArgumentParser(description='route generator for snap HTTP endpoints')
    parser.add_argument('-p', action='store_true', required=False, help='preview (show but do not generate) routes')
    parser.add_argument('-i', '--initfile', metavar='<initfile>', required=False, nargs=1, help='use the specified init file')
    args = parser.parse_args()

    config_filename = default_config_filename
    if args.initfile:
       config_filename = args.initfile[0]

    yaml_config = common.read_config_file(config_filename)    
    route_gen = RouteGenerator(yaml_config)
    
    j2env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'))
    template_mgr = common.JinjaTemplateManager(j2env)
    routing_module_template = template_mgr.get_template('routes.py.j2')
 
    print routing_module_template.render(router=route_gen)


if __name__ == '__main__':
   main(sys.argv[1:])
