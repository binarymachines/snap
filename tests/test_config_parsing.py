import unittest
from context import snap
import yaml



class ConfigfileLoadTest(unittest.TestCase):

    def setUp(self):
        with open('data/good_sample_config.yaml') as f:
            self.good_yaml_config = yaml.load(f)

        with open('data/bad_sample_config.yaml') as f:
            self.bad_yaml_config = yaml.load(f)


    def test_globals_should_contain_required_fields(self):
        self.fail()


    def test_service_object_config_should_contain_required_fields(self):
        self.fail()


    def test_datashape_config_should_contain_required_fields(self):
        self.fail()


    def test_transform_config_should_contain_required_fields(self):
        self.fail()


    def test_transform_config_should_not_reference_nonexistent_shape(self):
        self.fail()


    def test_transform_config_should_not_reference_invalid_request_method(self):
        self.fail()


    def test_error_handler_config_should_contain_required_fields(self):
        self.fail()


def main():
    unittest.main()

if __name__ == '__main__':
    main()
