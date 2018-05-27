import unittest
from context import snap
import os
import yaml


TEST_SVC_NAME = 'test_service'

class ConfigfileLoadTest(unittest.TestCase):

    def setUp(self):
        project_home = os.getenv('PROJECT_HOME')
        self.assertIsNotNone(project_home)
        good_config_file_path = os.path.join(project_home,
                                             'data/good_sample_config.yaml')

        bad_config_file_path = os.path.join(project_home,
                                            'data/bad_sample_config.yaml')
        
        with open(good_config_file_path) as f:
            self.good_yaml_config = yaml.load(f)

        with open(bad_config_file_path) as f:
            self.bad_yaml_config = yaml.load(f)


    def test_globals_should_contain_required_fields(self):
        required_fields = ['bind_host',
                           'port',
                           'debug',
                           'logfile',
                           'project_directory',
                           'transform_function_module',
                           'service_module',
                           'preprocessor_module']

        for field in required_fields:
            self.assertTrue(field in self.good_yaml_config['globals'])
        

    def test_service_object_config_should_contain_required_fields(self):
        svc_object_required_fields = ['class', 'init_params']
        init_param_fields = ['name', 'value']

        so_config = self.good_yaml_config['service_objects'][TEST_SVC_NAME]
        for field in svc_object_required_fields:            
            self.assertIn(field, so_config)


    def test_datashape_config_should_contain_required_fields(self):
        datashape_required_fields = ['fields']
        datashape_field_required_fields = ['name', 'datatype', 'required']

        self.assertIn('fields', self.good_yaml_config['data_shapes']['test_shape'])
        
        dsconfig = self.good_yaml_config['data_shapes']['test_shape']
        for field in datashape_field_required_fields:
            self.assertIn(field, dsconfig['fields'][0])


    def test_transform_config_should_contain_required_fields(self):
        transform_required_fields = ['route', 'method', 'input_shape', 'output_mimetype']
        transform_config = self.good_yaml_config['transforms']['test']
        for field in transform_required_fields:
            self.assertIn(field, transform_config)


    def test_transform_config_should_not_reference_nonexistent_shape(self):
        transform_config = self.good_yaml_config['transforms']['test']
        shape_name = transform_config['input_shape']
        self.assertIn(shape_name, self.good_yaml_config['data_shapes'])


    def test_transform_config_should_not_reference_invalid_request_method(self):
        valid_methods = 'GET', 'POST'
        transforms_table = self.good_yaml_config['transforms']
        for transform_name in transforms_table:
            transform = transforms_table[transform_name]
            self.assertIn(transform['method'], valid_methods)


    def test_error_handler_config_should_contain_required_fields(self):
        self.fail()


def main():
    unittest.main()

if __name__ == '__main__':
    main()
