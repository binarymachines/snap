#!/usr/bin/env python


class UnregisteredTestContextException(Exception):
    def __init__(self, scenario_name):
        Exception.__init__(self, 'No TestContext has been registered under the scenario name "%s".' % scenario_name)



class TestContext(object):
    def __init__(self, name, **kwargs):
        self._name = name
        self.__dict__.update(kwargs)
        #for name, value in kwargs.iteritems():
        #    self.__dict__.update((name, value))

    

class TestEnvironment(object):
    def __init__(self, **kwargs):
        self._data = {}


    def register_context(self, scenario_name, test_ctx):
        self._data[scenario_name] = test_ctx


    def load_context(self, scenario_name):
        if not self._data.get(scenario_name):
            raise UnregisteredTestContextException(scenario_name)
        return self._data[scenario_name]
    
