import unittest
import os
import yaml
from contextlib import contextmanager
import py_compile as pc
from snap import snap, common


GENERATED_APP_FILE = 'test_app.py'


class RouteGenerationTest(unittest.TestCase):

    def setUp(self):
        project_home = os.getenv('SNAP_TEST_HOME')
        if not project_home:
            raise Exception('the environment variable SNAP_TEST_HOME has not been set.')
            
        config_file_path = os.path.join(project_home,
                                        'data/good_sample_config.yaml')
        with open(config_file_path) as f:
            self.app_config = yaml.load(f)
        

    @contextmanager
    def assertDoesNotRaise(self, exc_type):
        try:
            yield None
        except exc_type:
            raise self.failureException('{} raised'.format(exc_type.__name__))

        
    def test_routegen_should_generate_a_valid_main_file(self):
        with self.assertDoesNotRaise(SyntaxError):
            pc.compile(GENERATED_APP_FILE)
            

    def test_routegen_should_add_to_transform_file_in_extend_mode(self):
        module_name = self.app_config['globals']['transform_function_module']
        transform_module = pc.importlib.import_module(module_name)        
        funcname = 'test_func'
        self.assertTrue(hasattr(transform_module, funcname))


    def test_default_function_should_raise_transform_not_implemented(self):
        module_name = self.app_config['globals']['transform_function_module']
        transform_module = pc.importlib.import_module(module_name)
        
        funcname = 'test_func'
        with self.assertRaises(snap.TransformNotImplementedException):                
            transform_function = getattr(transform_module, funcname)
            transform_function({}, common.ServiceObjectRegistry({}))

def main():
    unittest.main()

if __name__ == '__main__':
    main()
