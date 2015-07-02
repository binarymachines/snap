#!/usr/bin/env python


import yaml
import pip


class MissingModuleConfigSegmentException(Exception):
    def __init__(self, segment_name):
        Exception.__init__(self, 'No segment named "%s" found in yaml config.' % segment_name)



class SnapModule():
    def __init__(self, yaml_string, **kwargs):
        yaml_config = yaml.load(yaml_string)

        if not yaml_config:
            raise EmptyModuleConfigException()

        self._route = yaml_config.get('route')
        self._dependencies = yaml_config.get('dependencies', [])
        self._methods = yaml_config.get('methods')
        self._required_parameters = yaml_config.get('required_param_names', [])
 
        self.validate()


    def validate(self):
        if not self._route:
             raise MissingModuleConfigSegmentException('route')

        if not self._methods:
            raise MissingModuleConfigSegmentException('methods')

        # the 'dependencies' section is optional,
        # although it would be unusual for a module to have none


    # override in subclass
    def _handle_route(self, http_request, snap_service_registry, logger):
        return ''


    def handle_route(self, http_request, snap_service_registry, logger):
        return self._handle_route(http_request, snap_service_registry, logger)


    @property
    def route(self):
        return self._route


    @property
    def methods(self):
        return self._methods


    @property
    def dependencies(self):
        return self._dependencies


    @property
    def required_parameters(self):
        return self._required_parameters



class ModuleFrame():
    def __init__(self):
        self.modules = {}


    def load(self, snap_module, module_alias):
        self.modules[module_alias] = snap_module


    def install_dependencies(self, module_alias):
        for dep in self.get_dependencies(module_alias):
            pip.main(['install', dep])


    def get_module(self, module_alias):
        target_module = self.modules.get(module_alias)
        if not target_module:
            raise NoSuchModuleException(module_alias)
        return target_module


    def get_route(self, module_alias):
        target_module = self.get_module(module_alias)
        return target_module.route
    

    def get_dependencies(self, module_alias):
        target_module = self.get_module(module_alias)
        return target_module.dependencies


    def get_methods(self, module_alias):
        target_module = self.get_module(module_alias)
        return target_module.methods


    def get_required_parameters(self, module_alias):
        target_module = self.get_module(module_alias)
        return target_module.required_parameters



