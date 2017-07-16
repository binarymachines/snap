#!/usr/bin/env python

'''Usage:    snapconfig.py <app_name>

'''

from cmd import Cmd
import copy
import docopt
from docopt import docopt as docopt_func
from docopt import DocoptExit
import os
import re
import yaml
import logging
import jinja2
import common
from metaobjects import *
import config_templates
import cli_tools as cli

#pylint: disable=C0301
#pylint: disable=W0613


BAD_ROUTE_VAR_PROMPT = '''
It looks like you are attempting to specify a variable in this route.\n
To specify a route variable, use the form <datatype:routevar>.\n
If "datatype" is not one of [int, string, float, path],\n 
you must register a custom converter for your datatype,\n
otherwise Snap will fail to process the URL correctly at runtime.\n'''


BASIC_ROUTE_VAR_REGEX = re.compile(r'<\S+>')


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

            print '\nPlease specify one or more valid command parameters.'
            print e
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



class SnapConfigWriter(object):
    def __init__(self):
        pass

    def write(self, **kwargs):
        kwreader = common.KeywordArgReader('settings', 'transforms', 'shapes')
        kwreader.read(**kwargs)
        j2env = jinja2.Environment()
        template = j2env.from_string(config_templates.INIT_FILE)
        return template.render(global_settings=kwreader.get_value('settings'),
                               transforms=kwreader.get_value('transforms') or [],
                               data_shapes=kwreader.get_value('shapes') or [],
                               service_objects=kwreader.get_value('services') or [])


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

    @property
    def service_object_names(self):
        return [so.name for so in self.service_objects]


    @property
    def transform_names(self):
        return [t.name for t in self.transforms]


    @property
    def datashape_names(self):
        return [shape.name for shape in self.data_shapes]


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
            empty_shape = False
            print 'Add 1 or more fields to this datashape. (Enter "-" to create an empty shape.)'
            fields = []
            while True:
                missing_params = 3
                field_name = cli.InputPrompt('field name').show()
                if not field_name:
                    break
                elif field_name == '-':
                    empty_shape = True
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
            if missing_params and not empty_shape:
                return None
            if empty_shape:
                self.data_shapes.append(DataShapeMeta(shape_name, []))
            else:
                self.data_shapes.append(DataShapeMeta(shape_name, fields))
            return shape_name

        return None


    def edit_shape(self, shape_name):
        print '+++ Updating datashape "%s"' % shape_name
        shape = self.find_shape(shape_name)

        if not shape:
            print 'No such datashape has been registered.'
            return

        shape_index = self.get_shape_index(shape_name)

        opt_prompt = cli.MenuPrompt('Select operation', CHSHAPE_OPTIONS)
        operation = opt_prompt.show()

        while True:
            if not operation:
                break
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
        print '+++ Updating transform "%s"' % transform_name
        transform = self.find_transform(transform_name)

        if not transform:
            print 'No such transform has been registered.'
            return

        transform_index = self.get_transform_index(transform_name)
        opt_prompt = cli.MenuPrompt('Select operation',
                                    CHTFM_OPTIONS)
        operation = opt_prompt.show()
        while True:
            if not operation:
                break
            if operation == 'update_properties':
                transform = self.find_transform(transform_name)

                new_route = cli.InputPrompt('transform route',
                                            transform.route).show() or transform.route

                if not self.validate_route(new_route):
                    continue

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


    def make_svcobject(self, name=None):
        print '+++ Register new service object'
        so_name = name or cli.InputPrompt('service object name').show()
        so_classname = cli.InputPrompt('service object class').show()
        so_params = self.create_service_object_params()
        self.service_objects.append(ServiceObjectMeta(so_name, so_classname, **so_params))


    def edit_svcobject(self, so_name):
        print '+++ Updating service object'
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
            print '> No service object registered under the name %s.' % name
            return
        print common.jsonpretty(self.service_objects[index].data())


    def list_svcobjects(self):
        if not len(self.service_objects):
            print '[]'
            return
        for so in self.service_objects:
            print so.name


    def select_service_object(self):
        options = [{'value': name, 'label': name} for name in self.service_object_names]
        svc_object_name = cli.MenuPrompt('select service object', options).show()


    def make_transform(self, name=None):
        transform_name = name or cli.InputPrompt('transform name').show()
        if not transform_name:
            return
        route = cli.InputPrompt('transform route', '/%s' % transform_name).show()

        while True:
            if not route:
                return
            if not self.validate_route(route):
                route = cli.InputPrompt('transform route', '/%s' % transform_name).show()
            else:
                break

        method = cli.MenuPrompt('select method', METHOD_OPTIONS).show()
        if not method:
            return

        mimetype = cli.InputPrompt('output MIME type', DEFAULT_MIMETYPE).show()
        if not mimetype:
            return

        self.transforms.append(TransformMeta(transform_name, route, method, mimetype))

        print '> Creating new transform: %s' % transform_name
        self.edit_transform(transform_name)
        return


    def validate_route(self, route_string):
        if not route_string.startswith('/'):
            print 'the route string must start with "/".'
            return False

        if BASIC_ROUTE_VAR_REGEX.search(route_string) and route_string.find(':') == -1:
            print BAD_ROUTE_VAR_PROMPT
            return False

        if route_string.count(':') > 1:
            print BAD_ROUTE_VAR_PROMPT
            return False

        if not BASIC_ROUTE_VAR_REGEX.search(route_string) and route_string.find(':') > 0:
            print BAD_ROUTE_VAR_PROMPT
            return False

        return True



    def show_transform(self, transform_name):
        transform = self.find_transform(transform_name)
        if not transform:
            print '> No such transform found.'
            return

        config = self.get_config_data()
        print common.jsonpretty(transform.data(config))


    def list_transforms(self):
        if not len(self.transforms):
            print '[]'
            return
        for t in self.transforms:
            print t.name


    def select_transform(self):
        options = [{'value': name, 'label': name} for name in self.transform_names]
        transform_name = cli.MenuPrompt('select transform', options).show()
        return transform_name



    def show_shape(self, shape_name):
        shape = self.find_shape(shape_name)
        if not shape:
            print '> No such datashape found.'
            return
        print common.jsonpretty(shape.data())


    def list_shapes(self):
        if not len(self.data_shapes):
            print '[]'
            return
        for shape in self.data_shapes:
            print shape.name


    def select_shape(self):
        options = [{'value': name, 'label': name} for name in self.datashape_names]
        shape_name = cli.MenuPrompt('select datashape', options).show()
        return shape_name


    def edit_global_settings(self):
        print '> updating application settings...'
        settings_menu = []
        defaults = self.global_settings.current_values
        for key, value in defaults.iteritems():
            settings_menu.append({'label': key, 'value': key})

        while True:
            setting_name = cli.MenuPrompt('global setting to update', settings_menu).show()
            if not setting_name:
                break
            setting_value = cli.InputPrompt(setting_name, defaults[setting_name]).show()

            attr_name = 'set_%s' % setting_name
            setter_func = getattr(self.global_settings, attr_name)
            self.global_settings = setter_func(setting_value)

            should_continue = cli.InputPrompt('update another (Y/n)?', 'y').show()
            if should_continue.lower() != 'y':
                break


    def edit_global_setting(self, setting_name):
        if not setting_name in self.global_settings.current_values.keys():
            print "> No such global setting. Available global settings are: "
            print '\n'.join(['- %s' % (k) for k in self.global_settings.data().keys()])
            return

        defaults = self.global_settings.current_values
        setting_value = cli.InputPrompt(setting_name, defaults[setting_name]).show()
        attr_name = 'set_%s' % setting_name
        setter_func = getattr(self.global_settings, attr_name)
        self.global_settings = setter_func(setting_value)


    def show_global_settings(self):
        print common.jsonpretty(self.global_settings.data())



    @docopt_cmd
    def do_make(self, cmd_args):
        '''Usage:
                  make (transform | shape | svcobj)
                  make transform <name>
                  make shape <name>
                  make svcobj <name>
        '''

        object_name = cmd_args.get('<name>')

        if cmd_args['shape']:
            self.make_shape(object_name)
        elif cmd_args['svcobj']:
            self.make_svcobject(object_name)
        elif cmd_args['transform']:
            self.make_transform(object_name)


    def complete_make(self, text, line, begidx, endidx):
        MAKE_OPTIONS = ('transform', 'shape', 'svcobj')
        return [i for i in MAKE_OPTIONS if i.startswith(text)]


    @docopt_cmd
    def do_show(self, cmd_args):
        '''Usage:
                  show (transform | shape | svcobj)
                  show transform <name>
                  show shape <name>
                  show svcobj <name>
        '''

        object_name = cmd_args.get('<name>')

        if cmd_args['shape']:
            if object_name:
                self.show_shape(object_name)
            else:
                print 'Available DataShapes:'
                self.list_shapes()
        elif cmd_args['svcobj']:
            if object_name:
                self.show_svcobject(object_name)
            else:
                print 'Available ServiceObjects:'
                self.list_svcobjects()
        elif cmd_args['transform']:
            if object_name:
                self.show_transform(object_name)
            else:
                print 'Available Transforms:'
                self.list_transforms()


    def complete_show(self, text, line, begidx, endidx):
        SHOW_OPTIONS = ('transform', 'shape', 'svcobj')
        return [i for i in SHOW_OPTIONS if i.startswith(text)]


    @docopt_cmd
    def do_edit(self, arg):
        '''Usage:
                    edit (transform | shape | svcobj)
                    edit transform <name>
                    edit shape <name>
                    edit svcobj <name>'''

        object_name = arg.get('<name>')

        if arg['shape']:
            if not len(self.data_shapes):
                print 'You have not created any DataShapes yet.'
                return
            shape_name = object_name or self.select_shape()
            if shape_name:
                self.edit_shape(shape_name)
        elif arg['svcobj']:
            if not len(self.service_objects):
                print 'You have not created any ServiceObjects yet.'
                return
            svcobj_name = object_name or self.select_service_object()
            if svcobj_name:
                self.edit_svcobject(svcobj_name)
        elif arg['transform']:
            if not len(self.transforms):
                print 'You have not created any Transforms yet.'
                return
            transform_name = object_name or self.select_transform()
            if transform_name:
                self.edit_transform(transform_name)


    def complete_edit(self, text, line, begidx, endidx):
        EDIT_OPTIONS = ('transform', 'shape', 'svcobj')
        return [i for i in EDIT_OPTIONS if i.startswith(text)]


    @docopt_cmd
    def do_list(self, arg):
        '''Usage: list (transforms | shapes | svcobjs )'''

        if arg['shapes']:
            self.list_shapes()
        elif arg['svcobjs']:
            self.list_svcobjects()
        elif arg['transforms']:
            self.list_transforms()


    def complete_list(self, text, line, begidx, endidx):
        LIST_OPTIONS = ('transforms', 'shapes', 'svcobjs')
        return [i for i in LIST_OPTIONS if i.startswith(text)]


    @docopt_cmd
    def do_globals(self, arg):
        '''Usage:
                    globals [update]
                    globals set <setting_name>
                    globals set <setting_name> <setting_value>
        '''

        setting_name = arg.get('<setting_name>')
        if arg['update']:
            self.edit_global_settings()
        elif arg['set']:
            value = arg.get('<setting_value>')

            if value is None:
                self.edit_global_setting(setting_name)
            else:
                if not setting_name in self.global_settings.data().keys():
                    print "Available global settings are: "
                    print '\n'.join(['- %s' % (k) for k in self.global_settings.data().keys()])
                    return

                attr_name = 'set_%s' % name
                setter_func = getattr(self.global_settings, attr_name)
                self.global_settings = setter_func(value)

        else:
            self.show_global_settings()


    def complete_globals(self, text, line, begidx, endidx):
        GLOBALS_OPTIONS = ('update', 'set')
        return [i for i in GLOBALS_OPTIONS if i.startswith(text)]


    def yaml_config(self):
        cwriter = SnapConfigWriter()
        config = cwriter.write(settings=self.global_settings,
                               shapes=self.data_shapes,
                               transforms=self.transforms,
                               services=self.service_objects)
        return config


    def do_preview(self, arg):
        '''display current configuration in YAML format'''

        print self.yaml_config()


    def backup_file(self, filename):
        pass


    def write_file(self, filename):
        pass


    @docopt_cmd
    def do_save(self, arg):
        '''Usage:
                    save [filename]
                    save [-rb] <filename>

          Options:
                    -r  --replace   replace an existing file
                    -b  --backup    make a copy of the existing file
        '''

        should_backup = arg.get('--backup')
        should_overwrite = arg.get('--replace')

        output_filename = arg.get('filename') or arg.get('<filename>')
        if not output_filename:
            output_filename = cli.InputPrompt('output filename').show()
            if not output_filename:
                return

        if os.path.isdir(output_filename):
            print 'you have specified a directory, rather than a filename.'
            return

        if os.path.isfile(output_filename):
            if should_overwrite and should_backup:
                self.backup_file(output_filename)
            elif should_overwrite:
                self.write_file(output_filename)
            else:
                print 'the specified output file already exists.'
                return
        else:
            self.write_file(output_filename)


    def do_shell(self, s):
        os.system(s)

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

