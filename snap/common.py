#!/usr/bin/env python


import yaml
import os
import jinja2
from os.path import expanduser
import json
'''
# cross-compatible string type checking for python 2 and 3
try:
  basestring
except NameError:
  basestring = str
'''

class UnregisteredServiceObjectException(Exception):
    def __init__(self, alias):
        Exception.__init__(self, 'No ServiceObject registered under the alias "%s".' % alias)


class MissingEnvironmentVarException(Exception):
    def __init__(self, env_var):
        Exception.__init__(self, 'The following environment variables have not been set: %s' % env_var)


class MissingKeywordArgsException(Exception):
    def __init__(self, *keywords):
        Exception.__init__(self, 'The following required keyword arguments were not provided: %s' % (', '.join(keywords)))



class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


def read_config_file(filename):
    '''Load a YAML initfile by name, returning a dictionary of its contents

    '''
    config = None
    with open(filename, 'r') as filehandle:
        config = yaml.load(filehandle)
    return config



def full_path(filename):
    if filename.startswith(os.sep):
        return filename
    return os.path.join(os.getcwd(), filename)



def load_config_var(value):
    var = None
    if not value:
        pass
    elif value.__class__.__name__ == 'list':
        var = value
    elif isinstance(value, str):
        if value.startswith('$'):
            var = os.environ.get(value[1:])
            if not var:
                raise MissingEnvironmentVarException(value[1:])
        elif value.startswith('~%s' % os.path.sep):
            home_dir = expanduser(value[0])
            path_stub = value[2:]
            var = os.path.join(home_dir, path_stub)
        else:
            var = value
    else:
        var = value
    return var


def load_class(class_name, module_path):
    module_path_tokens = module_path.split('.')
    if len(module_path_tokens) == 1:
        module = __import__(module_path_tokens[0])
        return getattr(module, class_name)
    else:
        module = __import__(module_path)
        for index in range(1, len(module_path_tokens)):            
            module = getattr(module, module_path_tokens[index])
            
        return getattr(module, class_name)


def jsonpretty(data_dict):
    return json.dumps(data_dict, indent=4, sort_keys=True)


class JinjaTemplateManager(object):
    def __init__(self, j2_environment):
        self.environment = j2_environment


    def get_template(self, filename):
        return self.environment.get_template(filename)



def get_template_mgr_for_location(directory):
    j2env = jinja2.Environment(loader=jinja2.FileSystemLoader(directory))
    return JinjaTemplateManager(j2env)


class LocalEnvironment(object):
    def __init__(self, *envvars):
        self._env_vars = {}
        for var in envvars:
            self._env_vars[var] = None


    def init(self):
        missing_vars = []
        for var_name in self._env_vars.keys():
            value = os.getenv(var_name)
            if not value:
                missing_vars.append(var_name)
            else:
                self._env_vars[var_name] = value
        if len(missing_vars):
            raise MissingEnvironmentVarException(', '.join(missing_vars))


    def get_variable(self, name):
        if not name in self._env_vars.keys():
            raise Exception('The environment var "%s" was not registered with this LocalEnvironment.' % name)
        return self._env_vars[name]



class KeywordReadStatus(object):
    def __init__(self, error_msg_array):
        self._errors = error_msg_array
        if len(self._errors):
            self._is_ok = False
        else:
            self._is_ok = True

    @staticmethod
    def OK():
        return KeywordReadStatus([])

    @property
    def is_ok(self):
        return self._is_ok

    @property
    def errors(self):
        return self._errors


    @property
    def message(self):
        return ', '.join(self._errors)



class KeywordArgReader(object):
    def __init__(self, *required_keywords):
        self.values = {}
        self._required_keys = []
        for keyword in required_keywords:
            self._required_keys.append(keyword)


    @property
    def required_keywords(self):
        return self._required_keys


    def read(self, **kwargs):
        missing_keywords = []
        all_keys = set(self._required_keys)
        all_keys.update(kwargs.keys())
        
        for k in all_keys:
            if not kwargs.get(k) and k in self._required_keys:
                missing_keywords.append(k)
            else:
                self.values[k] = kwargs[k]

        if len(missing_keywords):
            raise MissingKeywordArgsException(*missing_keywords)
        return self


    def get_value(self, name):
        return self.values.get(name)


class ServiceObjectRegistry():
    def __init__(self, service_object_dictionary):
        self.services = service_object_dictionary


    def lookup(self, service_object_name):
        sobj = self.services.get(service_object_name)
        if not sobj:
            raise UnregisteredServiceObjectException(service_object_name)
        return sobj

