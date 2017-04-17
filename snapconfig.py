#!/usr/bin/env python

'''Usage:    snapconfig.py <app_name>

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


class TransformMeta(object):
    def __init__(self, name, route, method, output_mimetype, input_shape=None, **kwargs):
        self._name = name
        self._route = route
        self._method = method
        self._mime_type = output_mimetype
        if input_shape:
            self._input_shape_ref = input_shape.name
        else:
            self._input_shape_ref = kwargs.get('input_shape_name')


    @property
    def name(self):
        return self._name


    @property
    def input_shape(self):
        return self._input_shape_ref


    @property
    def route(self):
        return self._route


    def set_name(self, name):
        return TransformMeta(name,
                             self._route,
                             self._method,
                             self._mime_type,
                             None,
                             input_shape_name=self._input_shape_ref)


    def set_route(self, route):
        return TransformMeta(self._name,
                             route,
                             self._method,
                             self._mime_type,
                             None,
                             input_shape_name=self._input_shape_ref)


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
                             None,
                             input_shape_name=self._input_shape_ref)


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
        return DataShapeMeta(name, fields)


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
    def __init__(self, name, class_name, **kwargs):
        self._name = name
        self._classname = class_name
        self._init_params = []
        for param_name, param_value in kwargs.iteritems():
            self._init_params.append({'name': param_name, 'value': param_value})


    @property
    def name(self):
        return self._name


    @property
    def classname(self):
        return self._classname


    @property
    def init_params(self):
        return self._init_params


    def _params_to_dict(self, param_array):
        result = {}
        for p in param_array:
            result[p['name']] = p['value']
        return result


    def find_param_by_name(self, param_name):
        param = None
        for p in self._init_params:
            if p['name'] == param_name:
                param = p
                break
        return param


    def set_name(self, name):
        return ServiceObjectMeta(name, self._classname, **self._params_to_dict(self._init_params))


    def set_classname(self, classname):
        return ServiceObjectMeta(self._name, classname, **self._params_to_dict(self._init_params))


    def add_param(self, name, value):
        new_param_list = copy.deepcopy(self._init_params)
        new_param_list.append({'name': name, 'value': value})
        params = self._params_to_dict(new_param_list)

        return ServiceObjectMeta(self._name, self._classname, **params)


    def add_params(self, **kwargs):
        updated_so = self
        for name, value in kwargs.iteritems():
            updated_so = updated_so.add_param(name, value)
        return updated_so


    def remove_param(self, name):
        param = self.find_param_by_name(name)
        if not param:
            return self

        new_param_list = copy.deepcopy(self._init_params)
        new_param_list.remove(param)
        params = {}
        for p in new_param_list:
            params[p['name']] = p['value']

        return ServiceObjectMeta(self._name, self._classname, **params)


    def data(self):
        result = {'name': self._name,
                  'class': self._classname,
                  'init_params': self._init_params}
        return result



class GlobalSettingsMeta(object):
    def __init__(self, app_name, **kwargs):
        self._app_name = app_name
        self._bind_host = kwargs.get('bind_host') or '127.0.0.1'
        self._port = kwargs.get('port') or 5000
        self._debug = kwargs.get('debug') or True
        self._transform_module = kwargs.get('transform_module') or '%s_transforms' % self._app_name
        self._service_module = kwargs.get('service_module') or '%s_services' % self._app_name
        self._preprocessor_module = kwargs.get('preprocessor_module') or '%s_decode' % self._app_name
        self._project_directory = kwargs.get('project_directory') or  '$%s_HOME' % self._app_name.upper()
        self._logfile = kwargs.get('logfile') or '%s.log' % self._app_name


    @property
    def current_values(self):
        original_attrs = self.__dict__
        attrs = {}
        for key in original_attrs:
            if key != '_app_name':
                attrs[key.lstrip('_')] = original_attrs[key]
        return attrs


    def set_bind_host(self, host):
        new_attrs = self.current_values
        new_attrs['bind_host'] = host
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_app_name(self, name):
        new_attrs = self.current_values
        return GlobalSettingsMeta(name, **new_attrs)


    def set_port(self, port):
        new_attrs = self.current_values
        new_attrs['port'] = port
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_debug(self, debug_status):
        new_attrs = self.current_values
        new_attrs['debug'] = debug_status
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_transform_module(self, transform_module_name):
        new_attrs = self.current_values
        new_attrs['transform_module'] = transform_module_name
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_service_module(self, service_module_name):
        new_attrs = self.current_values
        new_attrs['service_module'] = service_module_name
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_preprocessor_module(self, preprocessor_module_name):
        new_attrs = self.current_values
        new_attrs['preprocessor_module'] = preprocessor_module_name
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_project_directory(self, project_directory):
        new_attrs = self.current_values
        new_attrs['project_directory'] = project_directory
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def set_logfile(self, logfile):
        new_attrs = self.current_values
        new_attrs['logfile'] = logfile
        return GlobalSettingsMeta(self._app_name, **new_attrs)


    def data(self):
        return self.current_values



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


    def do_mksvcobj(self, *cmd_args):
        print '+++ Register new service object'
        so_name = cli.InputPrompt('service object name').show()
        so_classname = cli.InputPrompt('service object class').show()
        so_params = self.create_service_object_params()
        self.service_objects.append(ServiceObjectMeta(so_name, so_classname, **so_params))


    def do_chsvcobj(self, *cmd_args):
        if not len(*cmd_args):
            print 'chsvcobj (change service object) command requires the service object name.'
            return

        print '+++ Update service object'
        so_name = cmd_args[0]
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


    def do_svcobj(self, *cmd_args):
        if not len(*cmd_args):
            print 'svcobj (show service object) command required the service object name.'
            return

        name = cmd_args[0]
        index = self.get_service_object_index(name)
        if index < 0:
            print 'no service object registered under the name %s.' % name

        print common.jsonpretty(self.service_objects[index].data())



    def do_mktfm(self, *cmd_args):
        transform_name = cli.InputPrompt('transform name').show()
        if not transform_name:
            return
        route = cli.InputPrompt('transform route', '/%s' % transform_name).show()
        method = cli.MenuPrompt('select method', METHOD_OPTIONS).show()
        mimetype = cli.InputPrompt('output MIME type', DEFAULT_MIMETYPE).show()

        self.transforms.append(TransformMeta(transform_name, route, method, mimetype))

        print 'Creating new transform: %s' % transform_name
        self.update_transform(transform_name)
        return


    def do_tfm(self, *cmd_args):
        if not len(*cmd_args):
            print 'tfm (show transform) command requires the transform name.'
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


    def do_shape(self, *cmd_args):
        if not len(*cmd_args):
            print 'shape (show datashape) command requires the datashape name.'
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


    def do_chsettings(self, *cmd_args):
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


    def do_settings(self, *cmd_args):
        print common.jsonpretty(self.global_settings.data())


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

