#!/usr/bin/env python

import os, sys
import argparse
import yaml
import jinja2
import common

default_config_filename = 'snap.conf'

RESERVED_ROUTES = ['smp']

class MissingHandlerFunctionException(Exception):
    def __init__(self, handler_name, handler_module_name):
        Exception.__init__(self, 'No function "%s" present in python module "%s.py"' % (handler_name, handler_module_name))


class NoSuchHandlerException(Exception):
    def __init__(self, handler_name):
        Exception.__init__(self, 'No handler registered under the alias "%s".' % handler_name)


class ReservedRouteException(Exception):
    def __init__(self, path):
        Exception.__init__(self, 'The URL route "%s" is reserved for internal use; please select a different path.' % path)



class Route(object):
    def __init__(self, name, urlPath, method_string, output_type):
        self.name = name
        self.path = urlPath
        self._methods = [method_name.strip() for method_name in method_string.split(',')]
        self.output_type = output_type


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
        #self.route_table = self.generate_routes_for_transforms(yaml_config)        
        self.handler_module_name = yaml_config['globals']['handler_module']
        #self.skeleton_transforms = self.generate_skeleton_transforms(self.route_table)
        
        #self.handler_table = self.load_handler_refs(self.handler_module_name, yaml_config)



    def generate_skeleton_transform_functions(self, yaml_config):
        route_table = self.generate_routes_for_transforms(yaml_config)
        
            
        

    '''
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
    '''
    

    def read_environment_value(self, val_name):
        '''Read a value (i.e. from a YAML file) in the standard format
        (leading dollar sign), indicating that the value resides in an
        environment variable
        '''
        return val_name[1:]


    def is_reserved_route(self, route_path):
        for path_element in RESERVED_ROUTES:
            if route_path.lstrip('/').startswith(path_element):
                return True
        return False


            
    def generate_routes_for_transforms(self, yaml_config):
        routes = {}
        transforms_segment =  yaml_config['transforms']
        for transform_name in transforms_segment:
            current_transform = transforms_segment[transform_name]
            route = current_transform['route']

            # certain routes are reserved for internal usage;
            # reject if found
            #
            if self.is_reserved_route(route):
                raise ReservedRouteException(path)

            methods = current_transform['method'].upper()
            output_mime_type = current_transform['output_mimetype']
            
            new_route = Route(transform_name, route, methods, output_mime_type)
            routes[transform_name] = new_route
            
        return routes

    
    def generate_transform_function_names(self, yaml_config):
        transforms_segment = yaml_config['transforms']
        return ['%s_transform' % f for f in transforms_segment]
        
        

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
 
    print routing_module_template.render(routes=route_gen.generate_routes_for_transforms(yaml_config),
                                         transforms=route_gen.generate_transform_function_names(yaml_config),
                                         handler_module = route_gen.handler_module_name)


if __name__ == '__main__':
   main(sys.argv[1:])
