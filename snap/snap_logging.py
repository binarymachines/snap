import logging
import logging.config


_log_config_filename = 'logging_config.ini'
logging.config.fileConfig(_log_config_filename)
root_logger = logging.getLogger()
root_logger.debug('SNAP logging config loaded from %s.' %_log_config_filename)

request_logger = logging.getLogger('request')
init_logger = logging.getLogger('init')
service_logger = logging.getLogger('service')
transform_logger = logging.getLogger('transform')
