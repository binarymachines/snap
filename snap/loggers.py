import logging
import logging.config
import pkgutil
import yaml

log_config_filename = 'logging_config.yaml'
yaml_config = yaml.load(pkgutil.get_data('snap', log_config_filename))

logging.config.dictConfig(yaml_config)
root_logger = logging.getLogger()
root_logger.debug('SNAP logging config loaded from %s.' % log_config_filename)

request_logger = logging.getLogger('request')
init_logger = logging.getLogger('init')
service_logger = logging.getLogger('service')
transform_logger = logging.getLogger('transform')
