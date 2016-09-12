#!/usr/bin/env python

'''Usage: routegen.py -g <initfile>
          routegen.py -p <initfile>
          routegen.py -e <initfile>

-g --generate  generate all code 
-e --extend    extend existing code
-p --preview   preview code generation

'''

import core
import os, sys
import argparse
import docopt
import yaml
import jinja2
import common
import re


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



class Transform(object):
    def __init__(self, name, input_shape, route, method_string, output_type, transform_function_module=None):
        self.name = name
        self.input_shape = input_shape
        self.route = route
        self._methods = [method_name.strip() for method_name in method_string.split(',')]
        self.output_type = output_type
        self.function_module_name = transform_function_module
        

    def get_methods(self):
        method_list = ["'%s'" % m for m in self._methods]
        return ', '.join(method_list)

    methods = property(get_methods)

    
    def get_function_name(self):
        if self.function_module_name: 
            return '%s.%s_func' % (self.function_module_name, self.name)
        return '%s_func' % self.name

    function_name = property(get_function_name)
    
    
    def get_route_variables(self):
        route_var_regex = re.compile(r'<[a-z]+>')
        return [match.group().lstrip('<').rstrip('>') for match in re.finditer(route_var_regex, self.route)]

    route_variables = property(get_route_variables)


        
class RouteGenerator():
    def __init__(self, yaml_config):        
        self.transform_function_module = yaml_config['globals'].get('transform_function_module')
        

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

    
    def load_shapes(self, yaml_config):
        data_shapes = {}

        shapes_segment = yaml_config['data_shapes']

        for shape_name in shapes_segment:
            if not shape_name.endswith('shape'):
                internal_shape_name = '%s_shape' % shape_name
            input_shape = core.InputShape(internal_shape_name)
            input_field_tables = shapes_segment[shape_name]['fields']
            if input_field_tables:
                for tbl in input_field_tables:
                    input_shape.add_field(tbl['name'], bool(tbl.get('required')))
                    
            data_shapes[shape_name] = input_shape
            
        return data_shapes
                

    
    def load_transforms(self, yaml_config):
        
        data_shapes = self.load_shapes(yaml_config)
        transforms = {}

        transforms_segment =  yaml_config['transforms']
        for transform_name in transforms_segment:
            current_transform = transforms_segment[transform_name]
            route = current_transform['route']

            # certain routes are reserved for internal usage;
            # reject if found
            #
            if self.is_reserved_route(route):
                raise ReservedRouteException(route)

            methods = current_transform['method'].upper()
            output_mime_type = current_transform['output_mimetype']
            
            new_transform = Transform(transform_name, 
                                      data_shapes.get(transform_name) or data_shapes.get('default'), 
                                      route, 
                                      methods, 
                                      output_mime_type,
                                      self.transform_function_module)
                              
            transforms[transform_name] = new_transform
            
        return transforms

    
    
    def generate_transform_function_names(self, yaml_config):
        transforms_segment = yaml_config['transforms']
        return ['%s_func' % f for f in transforms_segment]
        

ProgramMode = common.Enum(['GENERATE', 'EXTEND'])

        

def main(argv):
    try:
        args = docopt.docopt(__doc__)
        
        preview = args.get('--preview') or False        
        config_filename = args.get('<initfile>') or default_config_filename                    
        yaml_config = common.read_config_file(config_filename)    

        
        if args.get('--extend'):
            mode = ProgramMode.EXTEND
        elif args.get('--generate'):
            mode = ProgramMode.GENERATE
                
        route_gen = RouteGenerator(yaml_config)
    
        j2env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'))
        template_mgr = common.JinjaTemplateManager(j2env)

        transform_module_template = template_mgr.get_template('transforms.py.j2')
        transform_module_name = yaml_config['globals']['transform_function_module']
        transform_module_filename = '%s.py' % transform_module_name


        # are we generating or extending code?
        if mode == ProgramMode.GENERATE:
            transform_code = transform_module_template.render(transform_functions=route_gen.generate_transform_function_names(yaml_config))
            with open(transform_module_filename, 'w') as transform_file:
                transform_file.write(transform_code)

        else: # mode is ProgramMode.EXTEND
            # load existing transforms module
            tmodule = __import__(transform_module_name)
            
            # we will generate transform code for every function in the config file
            # that is not already defined in the module
            new_transforms = []
            for tname in route_gen.generate_transform_function_names(yaml_config):
                if not hasattr(tmodule, tname):
                    new_transforms.append(tname)

            transform_block_template = template_mgr.get_template('transform_funcs.py.j2')
            transform_code = transform_block_template.render(transform_functions=new_transforms)
            with open(transform_module_filename, 'a') as transform_file:
                transform_file.write('\n\n')
                transform_file.write(transform_code)
                

        routing_module_template = template_mgr.get_template('routes.py.j2')
        print routing_module_template.render(project_dir=yaml_config['globals']['project_directory'],
                                             transforms=route_gen.load_transforms(yaml_config),
                                             transform_module = route_gen.transform_function_module)

    except docopt.DocoptExit as e:
        print e.message
                                        
                                         
if __name__ == '__main__':
   main(sys.argv[1:])
