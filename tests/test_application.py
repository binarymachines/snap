import unittest
import os
import datetime
import time
import sh
import json
import requests
import yaml
#from context import snap
from snap import core
from snap import metaobjects as m


def tearDownModule():
    pass
    #app.process.terminate()


class HTTPServiceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pycmd = sh.Command('python')
        cls.app = pycmd('test_app.py', '--configfile=data/good_sample_config.yaml', _bg=True)
        time.sleep(1)
        if not cls.app.process.is_alive()[0]: # this method returns a tuple
            raise Exception('Error starting testbed application:\n%s' % cls.app.process.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.app.process.terminate()
        
        
    def setUp(self):
        self.project_home = os.getenv('SNAP_TEST_HOME')
        if not self.project_home:
            raise Exception('the environment var SNAP_TEST_HOME has not been set.')
        config_file_path = os.path.join(self.project_home,
                                        'data/good_sample_config.yaml')
        with open(config_file_path) as f:
            self.app_config = yaml.load(f)


    def test_should_listen_on_port_specified_in_config(self):
        port = self.app_config['globals']['port']
        r = requests.get('http://localhost:%s/ping' % port)
        self.assertEqual(r.status_code, 200)


    def test_should_reject_transform_requests_not_compliant_with_datashape(self):
        port = self.app_config['globals']['port']
        r = requests.get('http://localhost:%s/test' % port)
        self.assertEqual(r.status_code, 400)


    '''
    def test_should_accept_get_transform_requests_compliant_with_datashape(self):
        port = self.app_config['globals']['port']
        payload = {'placeholder': 'any_value'}

        #datashapes = m.load_shapes_from_yaml_config(self.app_config)
        
        r = requests.get('http://localhost:5000/test', data=payload)
        self.assertEqual(r.status_code, 200)
    '''

    def test_should_log_to_target_specified_in_config(self):
        logfile_name = self.app_config['globals']['logfile']
        logfile_path = os.path.join(self.project_home, logfile_name)
        statinfo = os.stat(logfile_path)
        initial_logfile_size = statinfo.st_size
        port = self.app_config['globals']['port']
        r = requests.get('http://localhost:%s/ping' % port)
        self.assertEqual(r.status_code, 200)

        statinfo = os.stat(logfile_path)
        final_logfile_size = statinfo.st_size
        self.assertGreater(final_logfile_size, initial_logfile_size)


    '''
    def test_default_content_protocol_can_decode_standard_content_types(self):
        protocol = core.default_content_protocol
        self.assertTrue(False)
    '''
    
    def test_custom_content_protocol_is_triggered_by_specified_content_type(self):
        port = self.app_config['globals']['port']
        headers = {'Content-Type': 'application/json'}
        payload = {'timestamp': datetime.datetime.now().isoformat()}
        r = requests.post('http://localhost:%s/posttest' % port,
                          data=json.dumps(payload),
                          headers=headers)
        
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertIn('test_decoder_called', response)


    
    

def main():
    unittest.main()


if __name__ == '__main__':
    main()
