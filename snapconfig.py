#!/usr/bin/env python

'''Usage:    snapconfig.py [<initfile>]

'''

from cmd import Cmd
import copy
import docopt
import os
import yaml
import logging
import common
import cli_tools as cli

#pylint: disable=C0301
#pylint: disable=W0613



CHSHAPE_OPTIONS = [{'value': 'add_field', 'label': 'Add field'},
                   {'value': 'change_field', 'label': 'Change field'}]


CHTFM_OPTIONS = [{'value': 'set_input_shape', 'label': 'Set input datashape'},
                 {'value': 'update_properties', 'label': 'Change transform properties'}]


METHOD_OPTIONS = [{'value': 'GET', 'label': 'HTTP GET'},
                  {'value': 'POST', 'label': 'HTTP POST'}]


BOOLEAN_OPTIONS = [{'value': True, 'label': 'True'},
                   {'value': False, 'label': 'False'}]


FIELD_TYPE_OPTIONS = [{'value': 'string', 'label': 'String'},
                      {'value': 'int', 'label': 'Integer'},
                      {'value': 'float', 'label': 'Float'},
                      {'value': 'date', 'label': 'Date'},
                      {'value': 'timestamp', 'label': 'Timestamp'},
                      {'value': 'bool', 'label': 'Boolean'},
                      {'value': 'char', 'label': 'Character'}]

DEFAULT_MIMETYPE = 'application/json'


class TransformMeta(object):
    def __init__(self, name, route, method, output_mimetype, input_shape=None):
        self._name = name
        self._route = route
        self._method = method
        self._mime_type = output_mimetype
        if input_shape:
            self._input_shape_ref = input_shape.name


    @property
    def name(self):
        return self._name


    @property
    def input_shape(self):
        return self._input_shape


    @property
    def route(self):
        return self._route


    def set_name(self, name):
        return TransformMeta(name,
                             self._route,
                             self._method,
                             self._mime_type,
                             self._input_shape)


    def set_route(self, route):
        return TransformMeta(self._name,
                             route,
                             self._method,
                             self._mime_type,
                             self._input_shape)


    def set_input_shape(self, input_shape):
        return TransformMeta(self._name,
                             self._route,
                             self._method,
                             self._mime_type,
                             input_shape)


    def set_method(self, method):
        return TransformMeta(self._name,
                             self._route,
                             method,
                             self._mime_type,
                             self._input_shape)


    def data(self, config_data):
        result = {'name': self._name,
                  'route': self._route,
                  'method': self._method,
                  'output_mimetype': self._mime_type}
        if self._input_shape_ref:
            result['input_shape'] = config_data['data_shapes'][self._input_shape_ref].data()

        return result



class DataShapeFieldMeta(object):
    def __init__(self, name, data_type, is_required=False):
        self.name = name
        self.data_type = data_type
        self.required = is_required


    def data(self):
        result = {'name': self.name,
                  'type': self.data_type}
        if self.required:
            result['required'] = True
        return result



class DataShapeMeta(object):
    def __init__(self, name, field_array):
        self._name = name
        self._fields = field_array


    @property
    def name(self):
        return self._name


    @property
    def fields(self):
        return self._fields


    def set_name(self, name):
        fields = copy.deepcopy(self.fields)
        return DataShapedMeta(name, fields)


    def add_field(self, f_name, f_type, is_required=False):
        fields = copy.deepcopy(self._fields)
        fields.append(DataShapeFieldMeta(f_name, f_type, is_required))
        return DataShapeMeta(self._name, fields)


    def replace_field(self, name, datashape_field):
        field_array = copy.deepcopy(self._fields)
        for i in range(0, len(field_array)):
            if field_array[i].name == name:
                field_array[i] = datashape_field
        return DataShapeMeta(self._name, field_array)


    def data(self):
        return {'name': self.name,
                'fields': [f.data() for f in self._fields]}



class ServiceObjectMeta(object):
    def __init__(self, name, **kwargs):
        self._name = name
        self._init_params = []
        for param_name, param_value in kwargs.iteritems():
            self._init_params.append({'name': param_name, 'value': param_value})



class SnapCLI(Cmd):
    def __init__(self):
        self.name = 'snapconfig'
        Cmd.__init__(self)
        self.prompt = '[%s] ' % self.name
        self.transforms = []
        self.data_shapes = []
        self.service_objects = []
        #self.replay_stack = Stack()


    def get_config_data(self):
        data = {'data_shapes': {}, 'transforms':{}, 'service_objects': {}}
        for shape in self.data_shapes:
            data['data_shapes'][shape.name] = shape

        for transform in self.transforms:
            data['transforms'][transform.name] = transform

        for so in self.service_objects:
            data['service_objects'][so.name] = so

        return data


    def find_shape(self, name):
        result = None
        for s in self.data_shapes:
            if s.name == name:
                result = s
                break

        return result


    def get_shape_index(self, name):
        for i in range(0, len(self.data_shapes)):
            if self.data_shapes[i].name == name:
                return i


    def find_transform(self, name):
        result = None
        for t in self.transforms:
            if t.name == name:
                result = t
                break

        return result


    def get_transform_index(self, name):
        for i in range(0, len(self.transforms)):
            if self.transforms[i].name == name:
                return i

        return -1


    def prompt_for_value(self, value_name):
        parameter_value = cli.InputPrompt('enter value for <%s>: ' % value_name).show()
        return parameter_value


    def do_quit(self, *cmd_args):
        print '%s CLI exiting.' % self.name
        raise SystemExit


    do_q = do_quit


    def update_shape_field(self, shape_field):
        missing_params = 3
        while True:
            field_name = cli.InputPrompt('field name', shape_field.name).show()
            if not field_name:
                break
            missing_params -= 1

            field_type = cli.MenuPrompt('field type', FIELD_TYPE_OPTIONS).show()
            if not field_type:
                break
            missing_params -= 1

            required = cli.MenuPrompt('required', BOOLEAN_OPTIONS).show()
            if required is None:
                break
            missing_params -= 1
            is_required = bool(required)
            break

        if not missing_params:
            return DataShapeFieldMeta(field_name, field_type, is_required)
        return None


    def create_shape_field(self):
        missing_params = 3
        field_name = None
        field_type = None
        is_required = None

        while True:
            field_name = cli.InputPrompt('field name').show()
            if not field_name:
                break
            missing_params -= 1

            field_type = cli.MenuPrompt('field type', FIELD_TYPE_OPTIONS).show()
            if not field_type:
                break
            missing_params -= 1

            required = cli.MenuPrompt('required', BOOLEAN_OPTIONS).show()
            if required is None:
                break
            missing_params -= 1
            is_required = bool(required)
            break

        if not missing_params:
            return DataShapeFieldMeta(field_name, field_type, is_required)
        return None


    def create_shape(self, *cmd_args):
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

                field_type = cli.MenuPrompt('field type', FIELD_TYPE_OPTIONS).show()
                if not field_type:
                    break
                missing_params -= 1

                required = cli.MenuPrompt('required', BOOLEAN_OPTIONS).show()
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


    def update_shape(self, shape_name):
        print 'Updating datashape "%s"' % shape_name
        shape = self.find_shape(shape_name)

        if not shape:
            print 'No such datashape has been registered.'
            return

        shape_index = self.get_shape_index(shape_name)

        opt_prompt = cli.MenuPrompt('Select operation', CHSHAPE_OPTIONS)
        operation = opt_prompt.show()

        while True:
            if operation == 'add_field':
                new_field = self.create_shape_field()
                if new_field:
                    shape = shape.add_field(new_field.name, new_field.data_type, new_field.required)
                break
            if operation == 'change_field':
                field_prompt = cli.MenuPrompt('Select field', shape.fields)
                field = field_prompt.show()
                updated_field = self.update_shape_field(field)
                if updated_field:
                    shape = shape.replace_field(field.name, updated_field)
                break
        self.data_shapes[shape_index] = shape



    def update_transform(self, transform_name):
        print 'Updating transform "%s"' % transform_name
        transform = self.find_transform(transform_name)

        if not transform:
            print 'No such transform has been registered.'
            return

        transform_index = self.get_transform_index(transform_name)
        opt_prompt = cli.MenuPrompt('Select operation',
                                    CHTFM_OPTIONS)
        operation = opt_prompt.show()
        while True:
            if operation == 'update_properties':
                transform = self.find_transform(transform_name)

                new_route = cli.InputPrompt('transform route',
                                            transform.route).show() or transform.route
                new_method = cli.MenuPrompt('select method',
                                            METHOD_OPTIONS).show() or transform.method

                transform = transform.set_route(new_route)
                transform = transform.set_method(new_method)
                self.transforms[transform_index] = transform
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
                    transform = transform.set_input_shape(self.find_shape(shape_name))
                    self.transforms[transform_index] = transform
                    break
                else:
                    shape_options = [{'value': s.name, 'label': s.name} for s in self.data_shapes]
                    shape_name = cli.MenuPrompt('Select an input shape for this transform', shape_options).show()
                    if not shape_name:
                        should_create_shape = cli.InputPrompt('Create a new datashape (Y/n)?', 'y').show().lower()
                        if should_create_shape == 'n':
                            break
                        shape_name = self.create_shape(transform_name)

                    transform = transform.set_input_shape(self.find_shape(shape_name))
                    self.transforms[transform_index] = transform
                    break


    def do_mktfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'mktfm (make transform) command requires the transform name.'
            return
        transform_name = cmd_args[0]
        route = cli.InputPrompt('transform route').show()
        method = cli.MenuPrompt('select method', METHOD_OPTIONS).show()
        mimetype = cli.InputPrompt('output MIME type', DEFAULT_MIMETYPE).show()

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

        config = self.get_config_data()
        print common.jsonpretty(transform.data(config))


    def do_lstfm(self, *cmd_args):
        '''list all transforms'''
        print '\n'.join([t.name for t in self.transforms])


    def do_chtfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'chtfm (change transform) command requires the transform name.'
            return

        transform_name = cmd_args[0]
        if not self.find_transform(transform_name):
            print 'no transform registered with name "".' % transform_name
            return

        self.update_transform(transform_name)


    def do_mkshape(self, *cmd_args):
        self.create_shape()


    def do_showshape(self, *cmd_args):
        if not len(*cmd_args):
            print 'showshape command requires the datashape name.'
            return
        shape_name = cmd_args[0]
        shape = self.find_shape(shape_name)
        if not shape:
            print 'No such datashape found.'
            return
        print common.jsonpretty(shape.data())


    def do_lsshape(self, *cmd_args):
        for shape in self.data_shapes:
            print shape.name


    def do_chshape(self, *cmd_args):
        if not len(*cmd_args):
            print 'chshape (change shape) command requires the datashape name.'
            return

        shape_name = cmd_args[0]
        if not self.find_shape(shape_name):
            print 'no datashape registered with name "".' % shape_name
            return

        self.update_shape(shape_name)


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

