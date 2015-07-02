#!/usr/env/bin python
#
# Entry point for snap modular plugin
#
# Here we define the data points that the plugin needs to expose
# in order to be loaded correctly by snap.
#
# The YAML configuration for a SnapModule must appear in the doc string, which 
# must start on the first non-whitespace line in the file.
#

'''
dependencies:
    - serpentine
    - sqlalchemy
    - mysql-python

methods:
    - GET
    - POST

route:
    testroute


service_objects:
    Test:
        class: 
            so_module.TestSO
        required_param_names: 
            - foo
            - bar
            - bazz
        
'''


from snapdev import SnapModule, ModuleFrame


class TestModule(SnapModule):
    def __init__(self):
        SnapModule.__init__(self, __doc__)


    def _handle_route(self, request, service_registry, logger):
        return 'this is a message from a prototype snap plugin.'



def main():
    tmod = TestModule()
    '''
    print 'route: %s' % tmod.route
    print 'dependencies:\n-%s' % '\n-'.join(tmod.dependencies)
    print 'method(s): %s' % tmod.methods
    '''

    frame = ModuleFrame()
    frame.load(tmod, 'test')
    #frame.install_dependencies('test')
    print frame.get_route('test')


if __name__ == '__main__':
    main()

