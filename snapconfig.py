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




mktfm_options = [{'value': 'add_shape', 'label': 'Add data shape'},
                 {'value': 'add_dimension', 'label': 'Add dimension'}]


method_options = [{'value': 'GET', 'label': 'HTTP GET'},
                  {'value': 'POST', 'label': 'HTTP POST'}]


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
    def __init__(self, name):
        self._name = name
        self._fields = []


    @property
    def name(self):
        return self._name


    @property
    def datatype(self):
        return self._type


    def add_field(self, f_name, f_type):        
        self._fields.append(DataShapeFieldMeta(f_name, f_type))


    def data(self):
        return { 'name': self.name, 'fields': self.fields }



class SnapCLI(Cmd):
    def __init__(self):
        self.name = 'snapconfig'
        Cmd.__init__(self)
        self.prompt = '[%s] ' % self.name    
        self.transforms = []
        #self.replay_stack = Stack()


    def find_transform(name):
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


    def create_shape_for_transform(self, transform_name):
        print 'Creating a new datashape for transform %s...' % transform_name
        shape_name = cli.InputPrompt('Enter a name for this datashape').show()
        if shape_name:
            print 'Add 1 or more fields to this datashape.'
            while True:
                field_name = cli.InputPrompt('field name').show()
                if not field_name:
                    break
                field_type = cli.MenuPrompt('field type', attribute_type_options).show()
                if not field_type:
                    break
                
                required = cli.MenuPrompt('required', required_options).show()
                if required is None:
                    break
                is_required = bool(required)

                print '> Added new field "%s" to datashape %s.' % (field_name, shape_name)

                fields.append(Field(field_name, field_type))
                should_continue = cli.InputPrompt('Add another field (Y/n)?', 'y').show()
                if should_continue == 'n':
                    break
            return Dimension(dim_name, fields)
        return None


    def update_transform(self, transform_name):
        opt_prompt = cli.MenuPrompt('Select operation', 
                                    mktfm_options)
        operation = opt_prompt.show()
        while True:            
            if operation == 'add_dimension':
                newdim = self.create_dimension_for_fact(fact_name)
                if newdim:
                    self.facts[fact_name]['dimensions'].append(newdim.data())
                    should_continue = cli.InputPrompt('Add another dimension (Y/n)?', 'y').show().lower()
                    if should_continue == 'n': 
                        break
                    
            if operation == 'add_fact_attr':
                newattr = self.create_attribute_for_fact(fact_name)
                if newattr:
                    self.facts[fact_name]['fields'].append(newattr.data())
                    should_continue = cli.InputPrompt('Add another attribute (Y/n)?', 'y').show().lower()
                    if should_continue == 'n': 
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
            

    def do_lstfm(self):
        print 'stub lstfm command'

    
    def do_chtfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'chfact command requires the transform name.'
            return

        transform_name = cmd_args[0]
        if not self.transforms.get(transform_name):
            print 'no transform registered with name "".' % transform_name
            return

        self.update_transform(transform_name)


    def do_mkshape(self, *cmd_args):
        print 'stub mkshape command'

    
    def do_lsshape(self):
        print 'stub lsshape command'


    def do_chshape(self):
        print 'stub chshape command'


def main(args):
    print args
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

