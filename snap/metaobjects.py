#!/usr/bin/env python

import copy
import re

from snap.constants import *


class BadRouteVariableFormatException(Exception):
    def __init__(self, name):
        Exception.__init__(self, 'Bad route variable "%s". Route vars must be specified in the format "<type:variable>".' % name)


class InvalidTransformNameException(Exception):
    def __init__(self, func_name):
        Exception.__init__(self, 'The transform name "%s" is not valid. Transform names must be valid Python function names.')


class TransformMeta(object):
    def __init__(self,
                 name,
                 route,
                 method,
                 output_mimetype,
                 input_shape=None,
                 **kwargs):

        if not VALID_FUNCTION_NAME_RX.match(name):
            raise InvalidTransformNameException(name)

        self._name = name
        self._route = route
        self._routevars = []
        self._method = method
        self._mime_type = output_mimetype
        if input_shape: 
            self._input_shape_ref = input_shape.name
        else:
            self._input_shape_ref = kwargs.get('input_shape_name')

        route_var_names = [match.group().lstrip('<').rstrip('>') for match in re.finditer(ROUTE_VARIABLE_REGEX, self._route)]

        for name in route_var_names:
            tokens = name.split(':')
            if not len(tokens) == 2:
                raise BadRouteVariableFormatException(name)
            self._routevars.append(tokens[1])


    @property
    def name(self):
        return self._name


    @property
    def method(self):
        return self._method


    @property
    def input_shape(self):
        return self._input_shape_ref


    @property
    def output_mimetype(self):
        return self._mime_type


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


    @property
    def field_names(self):
        return [f.name for f in self._fields]


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


def load_transforms_from_yaml_config(yaml_cfg):
    transforms = []
    for transform_name in yaml_cfg['transforms']:
        route = yaml_cfg['transforms'][transform_name]['route']
        method = yaml_cfg['transforms'][transform_name]['method']
        shape_name = yaml_cfg['transforms'][transform_name].get('input_shape')
        mime_type = yaml_cfg['transforms'][transform_name]['output_mimetype']

        transforms.append(TransformMeta(transform_name, route, method, mime_type, input_shape_name=shape_name))
    return transforms


def load_shape_fields_from_yaml_config(shape_name, yaml_cfg):
    fields = []
    for field in yaml_cfg['data_shapes'][shape_name].get('fields') or []:
        fields.append(DataShapeFieldMeta(field['name'], field['type'], field['required']))

    return fields


def load_shapes_from_yaml_config(yaml_cfg):
    shapes = []
    for shape_name in yaml_cfg['data_shapes']:
        fields = load_shape_fields_from_yaml_config(shape_name, yaml_cfg)
        shapes.append(DataShapeMeta(shape_name, fields))
    return shapes

def load_service_object_params_from_yaml_config(so_name, yaml_cfg):
    params = {}
    for param in yaml_cfg['service_objects'][so_name].get('init_params') or []:
        params[param['name']] = param['value']
    return params


def load_service_objects_from_yaml_config(yaml_cfg):
    service_objects = yaml_cfg.get('service_objects')
    if service_objects is None:
        service_objects = []
    for service_object_name in service_objects:
        so_class = yaml_cfg['service_objects'][service_object_name]['class']
        
        so_params = load_service_object_params_from_yaml_config(service_object_name, yaml_cfg)
        som = ServiceObjectMeta(service_object_name, so_class, **so_params)
        service_objects.append(som)
    return service_objects


def load_global_settings_from_yaml_config(yaml_cfg):    
    return yaml_cfg['globals']

