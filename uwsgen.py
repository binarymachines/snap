#!/usr/bin/env python
#
# uwsgen: uWSGI initfile generator for snap microservices 
# 
#
# Note: the docopt usage string must start on the first non-comment, non-whitespace line.
#

"""Usage: 
        uwsgen.py [--env=<environment> | --list] <configfile> 
        uwsgen.py -h | --help

Arguments:
        <configfile>      yaml configuration filename
Options:
        --env=<environment>       named configuration context in config file
        --list                    list the available contexts
"""


from docopt import docopt
import yaml
import jinja2
import os, sys
import common




class UWSGIEnvironment():
    def __init__(self, base_dir, python_home, socket_dir, log_dir):
        self.base_dir = common.load_config_var(base_dir)
        self.python_home = common.load_config_var(python_home)
        self.socket_dir = common.load_config_var(socket_dir)
        self.log_dir = common.load_config_var(log_dir)

    def __repr__(self):
        lines [self. self.virtualenv_dir, self.python_dir, self.socket_dir, self.log_dir]
        return '\n'.join(lines)


def load_uwsgi_environments(yaml_config):
    config_section = yaml_config['uwsgi_environments']

    environments = {}
    for env_name in config_section:
        base_dir = config_section[env_name]['base_directory']
        python_home = config_section[env_name]['python_home']
        socket_dir = config_section[env_name]['socket_directory']
        log_dir = config_section[env_name]['log_directory']

        new_env = UWSGIEnvironment(base_dir, python_home, socket_dir, log_dir)
        environments[env_name] = new_env

    return environments
        
        


if __name__ == '__main__':

    args =  docopt(__doc__)


    config_filename = common.full_path(args['<configfile>'])

    env = args['--env']
    yaml_config = common.read_config_file(config_filename)
    env_table = load_uwsgi_environments(yaml_config)
    
    if not len(env_table.keys()):
        print 'No uWSGI environment found in config file. Exiting.\n'
        exit(0)

    if args['--list']:
        print 'Available uWSGI environments in %s:' % config_filename
        print '\n'.join(env_table.keys()) 
        exit(0)
    
    target_env = None
    if not env and len(env_table.keys()) > 1:
        print 'The uWSGI config in file %s contains multiple environments. Please specify a target environment.' % args['<configfile>']
        exit(0)

    elif not env:
        target_env = env_table.values[0]
    else:
        target_env = env_table.get(env)
        
    if not target_env:
        print 'No uWSGI environment "%s" found in config file. Exiting.'
        exit(0)

    
    j2env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'))
    template_mgr = common.JinjaTemplateManager(j2env)
    initfile_template = template_mgr.get_template('snap_uwsgi.ini.j2')
    
    print '%s\n\n' % initfile_template.render(uwsgi_config=target_env)

    
    
    
