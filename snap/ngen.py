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
        return '%s:\n--hostname: %s\n--port: %s\n--uWSGI socket: %s' % (self.name, 
                                                                   self.hostname, 
                                                                   self.port, 
                                                                   self.uwsgi_sockfile)



def load_nginx_config_table(yaml_config_obj):
    configs = {}
    config_section = yaml_config_obj['nginx_servers']
    for server_name in config_section:
        host = config_section[server_name]['hostname']
        port = config_section[server_name]['port']
        uwsgi_socketfile = config_section[server_name]['uwsgi_sock']
        configs[server_name] = NginxConfig(server_name, host, port, uwsgi_socketfile)

    return configs
        
        



def main():
    args = docopt(__doc__)

    config_filename = common.full_path(args['<configfile>'])
    yaml_config = common.read_config_file(config_filename)
    configs = load_nginx_config_table(yaml_config)
    template_mgr = common.get_template_mgr_for_location('templates')
    config_template = template_mgr.get_template('nginx_config.j2')

    # show all the configurations
    #
    if args['-l'] or args['--list']:        
        for key in configs.keys():
            print configs[key]

        exit(0)
        
    # we can generate without a specific nginx config, iff there's just one
    #
    output = None
    config_name = args['--env']

    if args['<configfile>'] and not config_name:
        if len(configs.keys()) > 1:
            print 'Multiple configurations found. Please specify one.'
            exit(0)        
        output = config_template.render(nginx_config=configs.values()[0])
        
    else:
        if not configs.get(config_name):
            print 'No nginx configuration labeled "%s" in %s.' % (config_name, config_filename)
            exit(0)
        output = config_template.render(nginx_config=configs[config_name])
        
    print output
    exit(0)
        


    

if __name__=='__main__':
    main()
