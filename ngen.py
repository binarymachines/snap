#!/usr/bin/env python
#
# ngen: nginx initfile generator for snap microservices 
# 
#
# Note: the docopt usage string must start on the first non-comment, non-whitespace line.
#

"""Usage: 
        ngen.py [--env=<environment>] <configfile> 
        ngen.py (-l | --list) <configfile>
        ngen.py (-d | --describe) <environment> <configfile>
        ngen.py (-h | --help)

Arguments:
        <configfile>      yaml configuration filename
Options:
        --env=<environment>             named execution context in config file

"""


from docopt import docopt
import yaml
import jinja2
import os, sys
import common


class NginxConfig():
    def __init__(self, name, hostname, port, socket_file):
        self.name = name
        self.hostname = hostname
        self.port = port
        self.uwsgi_sockfile = socket_file


    def __repr__(self):
        return '--%s:\nhostname: %s\port: %s\nuWSGI socket: %s' % (self.name, 
                                                                   self.hostname, 
                                                                   self.port, 
                                                                   self.uwsgi_sockfile)



def get_nginx_configs_as_list(yaml_config_obj):
    



def main():
    args = docopt(__doc__)
    
    #print args

    config_filename = common.full_path(args.configfile)
    yaml_config = common.read_config_file(config_filename)

    if args.l:
        configs = get_nginx_configs_as_list(yaml_config)
        print '\n'.join(configs)
        exit(0)


    

if __name__=='__main__':
    main()
