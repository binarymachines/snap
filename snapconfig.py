#!/usr/bin/env python

'''Usage:    snapconfig.py <app_name>

'''

from cmd import Cmd
import copy
import docopt
from docopt import docopt as docopt_func
from docopt import DocoptExit
import os
import yaml
import logging
import common
from metaobjects import *
import cli_tools as cli

#pylint: disable=C0301
#pylint: disable=W0613



CHSHAPE_OPTIONS = [{'value': 'add_field', 'label': 'Add field'},
                   {'value': 'change_field', 'label': 'Change field'}]


CHTFM_OPTIONS = [{'value': 'set_input_shape', 'label': 'Set input datashape'},
                 {'value': 'update_properties', 'label': 'Change transform properties'}]


CHSO_OPTIONS = [{'value': 'add_params', 'label': 'Add one or more input params'},
                {'value': 'remove_params', 'label': 'Remove one or more input params'}]


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


def docopt_cmd(func):
    """
    This decorator is used to simplify the try/except block and pass the result
    of the docopt parsing to the called action.
    """
    def fn  (self, arg):
        try:
            opt = docopt_func(fn.__doc__, arg)

        except DocoptExit as e:
            # The DocoptExit is thrown when the args do not match.
            # We print a message to the user and the usage block.

            print('\nPlease specify one or more command parameters.')
            print(e)
            return

        except SystemExit:
            # The SystemExit exception prints the usage for --help
            # We do not need to do the print here.

            return

        return func(self, opt)

    fn.__name__ = func.__name__
    fn.__doc__ = func.__doc__
    fn.__dict__.update(func.__dict__)
    return fn



class SnapCLI(Cmd):
    def __init__(self, app_name):
        self.name = 'snapconfig'
        Cmd.__init__(self)
        self.prompt = '[%s] ' % self.name
        self.transforms = []
        self.data_shapes = []
        self.service_objects = []
        self.global_settings = GlobalSettingsMeta(app_name)
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


    def find_service_object(self, name):
        result = None
        for so in self.service_objects:
            if so.name == name:
                result = so
                break
        return result


    def get_service_object_index(self, name):
        result = -1
        for i in range(0, len(self.service_objects)):
            if self.service_objects[i].name == name:
                result = i
                break
        return result


    def find_shape(self, name):
        result = None
        for s in self.data_shapes:
            if s.name == name:
                result = s
                break

        return result


    def get_shape_index(self, name):
        result = -1
        for i in range(0, len(self.data_shapes)):
            if self.data_shapes[i].name == name:
                result = i
                break
        return result


    def find_transform(self, name):
        result = None
        for t in self.transforms:
            if t.name == name:
                result = t
                break
        return result


    def get_transform_index(self, name):
        result = -1
        for i in range(0, len(self.transforms)):
            if self.transforms[i].name == name:
                result = i
                break
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


    def make_shape(self, name=None):
        shape_name = name or cli.InputPrompt('Enter a name for this datashape').show()
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


    def edit_shape(self, shape_name):
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



    def edit_transform(self, transform_name):
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
                    shape_name = self.make_shape()
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
                        shape_name = self.make_shape(shape_name)

                    transform = transform.set_input_shape(self.find_shape(shape_name))
                    self.transforms[transform_index] = transform
                    break


    def create_service_object_params(self):
        so_params = {}
        while True:
            param_name = cli.InputPrompt('parameter name').show()
            if not param_name:
                break
            param_value = cli.InputPrompt('parameter value').show()
            if not param_value:
                break

            so_params[param_name] = param_value

            should_continue = cli.InputPrompt('add another parameter (Y/n)?', 'y').show()
            if should_continue.lower() != 'y':
                break

        return so_params

    
    def make_svcobject(self, name):
        print '+++ Register new service object'
        so_name = name or cli.InputPrompt('service object name').show()
        so_classname = cli.InputPrompt('service object class').show()
        so_params = self.create_service_object_params()
        self.service_objects.append(ServiceObjectMeta(so_name, so_classname, **so_params))


    def edit_svcobject(self, so_name):
        print '+++ Update service object'
        so_index = self.get_service_object_index(so_name)
        if so_index < 0:
            print 'No service object registered under the name %s.' % so_name
            return

        current_so = self.service_objects[so_index]
        so_name = cli.InputPrompt('change name to', current_so.name).show()
        self.service_objects[so_index] = current_so.set_name(so_name)
        current_so = self.service_objects[so_index]

        so_classname = cli.InputPrompt('change class to', current_so.classname).show()
        self.service_objects[so_index] = current_so.set_classname(so_classname)
        current_so = self.service_objects[so_index]

        operation = cli.MenuPrompt('select service object operation', CHSO_OPTIONS).show()
        if operation == 'add_params':
            new_params = self.create_service_object_params()
            self.service_objects[so_index] = current_so.add_params(new_params)
            current_so = self.service_objects[so_index]

        if operation == 'remove_params':
            while True:
                param_menu = [{'label': p.name, 'value': p.name} for p in current_so.init_params]
                param_name = cli.MenuPrompt('select param to remove', param_menu).show()
                self.service_objects[so_index] = current_so.remove_param(param_name)
                current_so = self.service_objects[so_index]

                should_continue = cli.InputPrompt('remove another (y/n)?', 'Y').show()
                if should_continue.lower() != 'y':
                    break


    def show_svcobject(self, name):
        index = self.get_service_object_index(name)
        if index < 0:
            print 'no service object registered under the name %s.' % name

        print common.jsonpretty(self.service_objects[index].data())


    def list_svcobjects(self):
        for so in self.service_objects:
            print so.name()


    def make_transform(self, name):
        transform_name = name or cli.InputPrompt('transform name').show()
        if not transform_name:
            return
        route = cli.InputPrompt('transform route', '/%s' % transform_name).show()
        method = cli.MenuPrompt('select method', METHOD_OPTIONS).show()
        mimetype = cli.InputPrompt('output MIME type', DEFAULT_MIMETYPE).show()

        self.transforms.append(TransformMeta(transform_name, route, method, mimetype))

        print 'Creating new transform: %s' % transform_name
        self.edit_transform(transform_name)
        return


    def show_transform(self, transform_name):
        transform = self.find_transform(transform_name)
        if not transform:
            print 'No such transform found.'
            return

        config = self.get_config_data()
        print common.jsonpretty(transform.data(config))


    def list_transforms(self):
        '''list all transforms'''
        print '\n'.join([t.name for t in self.transforms])



    def show_shape(self, shape_name):
        shape = self.find_shape(shape_name)
        if not shape:
            print 'No such datashape found.'
            return
        print common.jsonpretty(shape.data())


    def list_shapes(self):
        for shape in self.data_shapes:
            print shape.name


    def edit_globals(self):
        print 'updating application settings...'
        settings_menu = []
        defaults = self.global_settings.current_values
        for key, value in defaults.iteritems():
            settings_menu.append({'label': key, 'value': key})

        while True:
            setting_name = cli.MenuPrompt('global setting to update', settings_menu).show()
            setting_value = cli.InputPrompt(setting_name, defaults[setting_name]).show()

            attr_name = 'set_%s' % setting_name
            setter_func = getattr(self.global_settings, attr_name)
            self.global_settings = setter_func(setting_value)

            should_continue = cli.InputPrompt('update another (Y/n)?', 'y').show()
            if should_continue.lower() != 'y':
                break


    def show_globals(self):
        print common.jsonpretty(self.global_settings.data())



    def show_help_prompt(self, cmd_name):
        print 'PLACEHOLDER: show user additional options for the %s command' % cmd_name


    @docopt_cmd
    def do_make(self, cmd_args):
        '''Usage: make (shape | svcobject | transform | ?)
                  make shape <name>
                  make svcobject <name>
                  make transform <name>
        '''

        object_name = cmd_args.get('name')

        if cmd_args['?']:
            self.show_help_prompt('make')
        elif cmd_args['shape']:
            self.make_shape(object_name)
        elif cmd_args['svcobject']:
            self.make_svcobject(object_name)
        elif cmd_args['transform']:
            self.make_transform(object_name)


    @docopt_cmd
    def do_show(self, cmd_args):
        '''Usage: show (shape | svcobject | transform | ?)
                  show shape <name>
                  show svcobject <name>
                  show transform <name>
        '''

        object_name = cmd_args.get('name')

        if cmd_args['?']:
            self.show_help_prompt('show')
        elif cmd_args['shape']:
            if object_name:
                self.show_shape(object_name)
            else:
                self.list_shapes()
        elif cmd_args['svcobject']:
            if object_name:
                self.show_svcobject(object_name)
            else:
                self.list_svcobjects()
        elif cmd_args['transform']:
            if object_name:
                self.show_transform(object_name)
            else:
                self.list_transforms()


    @docopt_cmd
    def do_edit(self, arg):
        '''Usage: edit (shape | svcobj | transform | ?)'''

        if arg['?']:
            self.show_help_prompt('edit')


    @docopt_cmd
    def do_list(self, arg):
        '''Usage: list (shapes | svcobjects | transforms | ?)'''

        if arg['?']:
            self.show_help_prompt('list')


    def do_globals(self, arg):
        self.show_globals()


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

    app_name = args['<app_name>']
    snap_cli = SnapCLI(app_name)
    snap_cli.cmdloop()


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)

