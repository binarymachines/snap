#!/usr/bin/env python

'''Usage:    snapconfig.py [<initfile>]

'''

from cmd import Cmd
import docopt
import os, sys
import yaml
import logging
import snap, common
import cli_tools as cli




chtfm_options = [{'value': 'set_input_shape', 'label': 'Set input datashape'},
                 {'value': 'update_properties', 'label': 'Change transform properties'}]


method_options = [{'value': 'GET', 'label': 'HTTP GET'},
                  {'value': 'POST', 'label': 'HTTP POST'}]


boolean_options = [{'value': True, 'label': 'True'}, 
                   {'value': False, 'label': 'False'}]


field_type_options = [{'value': 'string', 'label': 'String'},
                          {'value': 'int', 'label': 'Integer'}, 
                          {'value': 'float', 'label': 'Float'},
                          {'value': 'date', 'label': 'Date'},
                          {'value': 'timestamp', 'label': 'Timestamp'},
                          {'value': 'bool', 'label': 'Boolean'},
                          {'value': 'char', 'label': 'Character'}]

default_mimetype = 'application/json'


class TransformMeta(object):
    def __init__(self, name, route, method, output_mimetype):
        self._name = name
        self._route = route
        self._method = method
        self._mime_type = output_mimetype
        self._input_shape = None

    @property
    def name(self):
        return self._name
        
    def set_input_shape(self, input_shape):
        self._input_shape = input_shape


    def data(self):
        result = {'name': self._name, 
                'route': self._route,
                'method': self._method,
                'output_mimetype': self._mime_type}
        if self._input_shape:
            result['input_shape'] = self._input_shape.data()

        return result



class DataShapeFieldMeta(object):
    def __init__(self, name, data_type, is_required=False):
        self.name = name
        self.data_type = data_type
        self.required = is_required


    def data(self):
        result = {'name': self.name, 
                  'type': self.data_type }
        if self.required:
            result['required'] = True



class DataShapeMeta(object):
    def __init__(self, name, field_array):
        self._name = name
        self._fields = field_array


    @property
    def name(self):
        return self._name


    def add_field(self, f_name, f_type, is_required=False):        
        self._fields.append(DataShapeFieldMeta(f_name, f_type, is_required))


    def data(self):
        return { 'name': self.name, 'fields': self.fields }



class SnapCLI(Cmd):
    def __init__(self):
        self.name = 'snapconfig'
        Cmd.__init__(self)
        self.prompt = '[%s] ' % self.name    
        self.transforms = []
        self.data_shapes = []
        #self.replay_stack = Stack()

    
    def find_shape(self, name):
        result = None
        for s in self.data_shapes:
            if s.name == name:
                result = s
                break

        return result


    def find_transform(self, name):
        result = None
        for t in self.transforms:
            if t.name == name:
                result = t
                break

        return result


    def prompt_for_value(self, value_name):
        parameter_value = cli.InputPrompt('enter value for <%s>: ' % value_name).show()
        return parameter_value


    def do_quit(self, *cmd_args):
        print '%s CLI exiting.' % self.name
        raise SystemExit


    do_q = do_quit


    def create_shape(self):

        shape_name = cli.InputPrompt('Enter a name for this datashape').show()
        if shape_name:
            print 'Add 1 or more fields to this datashape.'
            fields = []
            while True:
                missing_params = 3
                field_name = cli.InputPrompt('field name').show()
                if not field_name:
                    break
                missing_params -= 1

                field_type = cli.MenuPrompt('field type', field_type_options).show()
                if not field_type:
                    break
                missing_params -= 1

                required = cli.MenuPrompt('required', boolean_options).show()
                if required is None:
                    break
                missing_params -= 1
                is_required = bool(required)

                print '> Added new field "%s" to datashape %s.' % (field_name, shape_name)
               
                fields.append(DataShapeFieldMeta(field_name, field_type, is_required))
                should_continue = cli.InputPrompt('Add another field (Y/n)?', 'y').show()
                if should_continue == 'n':
                    break
            if missing_params:
                return None
            
            self.data_shapes.append(DataShapeMeta(shape_name, fields))
            return shape_name
        return None


    def update_transform(self, transform_name):
        print 'Updating transform "%s"' % transform_name
        transform = self.find_transform(transform_name)

        if not transform:
            print 'No such transform has been registered.'
            return

        opt_prompt = cli.MenuPrompt('Select operation', 
                                    mktfm_options)
        operation = opt_prompt.show()
        while True:         
            if operation == 'update_properties':
                transform = self.find_transform(transform_name)
                transform_index = self.get_transform_index(transform_name)
                
                new_route = cli.InputPrompt('transform route').show() or transform._route                
                new_method = cli.MenuPrompt('select method', method_options).show() or transform._method

                self.transforms[transform_index].set_route(new_route)
                self.transforms[transform_index].set_method(new_method)

                break

            if operation == 'set_input_shape':
                if not len(self.data_shapes):
                    should_create_shape = \
                        cli.InputPrompt('You have not created any datashapes yet. Create one now (Y/n)?', 
                                        'y').show().lower()
                    if should_create_shape == 'n':
                        break
                    print 'Creating the input datashape for transform "%s"...' % transform_name
                    shape_name = self.create_shape()
                    transform.set_input_shape(self.find_shape(shape_name))
                    break
                else:
                    shape_options = [{ 'value': s.name, 'label': s.name} for s in self.data_shapes]
                    shape_name = cli.MenuPrompt('Select an input shape for this transform', shape_options).show()
                    if not shape_name:
                        should_create_shape = cli.InputPrompt('Create a new datashape (Y/n)?', 'y').show().lower()
                        if should_create_shape == 'n':
                            break
                        shape_name = self.create_shape(transform_name)
                        
                    transform.set_input_shape(self.find_shape(shape_name))
                    break


    def do_mktfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'mktfm (make transform) command requires the transform name.'
            return
        transform_name = cmd_args[0]
        route = cli.InputPrompt('transform route').show()
        method = cli.MenuPrompt('select method', method_options).show()
        mimetype = cli.InputPrompt('output MIME type',  default_mimetype).show()
        
        self.transforms.append(TransformMeta(transform_name, route, method, mimetype))
            
        print 'Creating new transform: %s' % transform_name
        self.update_transform(transform_name)
        return 
    

    def do_showtfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'showtfm (show transform) command requires the transform name.'
            return
        transform_name = cmd_args[0]
        transform = self.find_transform(transform_name)
        if not transform:
            print 'No such transform found.'
            return
        print transform.data()


    def do_lstfm(self, *cmd_args):
        print '\n'.join([t.name for t in self.transforms])

    
    def do_chtfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'chfact command requires the transform name.'
            return

        transform_name = cmd_args[0]
        if not self.find_transform(transform_name):
            print 'no transform registered with name "".' % transform_name
            return

        self.update_transform(transform_name)


    def do_mkshape(self, *cmd_args):
        print 'stub mkshape command'

    
    def do_lsshape(self):
        print 'stub lsshape command'


    def do_chshape(self):
        print 'stub chshape command'


    def emptyline(self):
        pass


def main(args):
    '''
    init_filename = args['initfile']
    yaml_config = common.read_config_file(init_filename)
    log_directory = yaml_config['globals']['log_directory']
    log_filename = 'forge.log'
    log = metl.init_logging('mx_forge', os.path.join(log_directory, log_filename), logging.DEBUG)
    '''
    
    snap_cli = SnapCLI()
    snap_cli.cmdloop()
    

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)

