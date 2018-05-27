import unittest
import snap
import os
import yaml
from scripts import routegen as rg


class RouteGenerationTest(unittest.TestCase):

    def setUp(self):
        pass
        '''
        project_home = os.getenv('TEST_HOME')
        self.assertIsNotNone(project_home)
        config_file_path = os.path.join(project_home,
                                        'data/good_sample_config.yaml')
        with open(config_file_path) as f:
            self.app_config = yaml.load(f)
        self.route_gen = rg.RouteGenerator(self.app_config)
        '''
        
    
    def test_routegen_should_generate_a_valid_main_file(self):
        pass


    def test_routegen_should_generate_one_route_per_transform(self):
        self.assertTrue(False)


    def test_routegen_should_add_to_transform_file_in_extend_mode(self):
        self.assertTrue(False)


    def test_routegen_should_replace_transform_file_in_generate_mode(self):
        self.assertTrue(False)


    def test_routegen_should_not_add_whitespace_to_transform_file(self):
        self.assertTrue(False)


    def test_default_function_should_raise_transform_not_implemented(self):
        self.assertTrue(False)


def main():
    unittest.main()

if __name__ == '__main__':
    main()
