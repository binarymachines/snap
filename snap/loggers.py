import logging
import logging.config
import pkgutil
import yaml
from snap import snap

#logging.config.dictConfig(snap.logging_config)
root_logger = logging.getLogger()
request_logger = logging.getLogger('request')
init_logger = logging.getLogger('init')
service_logger = logging.getLogger('service')
transform_logger = logging.getLogger('transform')
