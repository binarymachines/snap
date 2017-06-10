#!/usr/bin/env python

'''Usage: mkinitfile.py <project_name> [-d <project_directory>]

   Options:

        -d, --dir:   directory
'''



import docopt
import jinja2
import common
import os



def main(args):
    project_name = args['<project_name>']
    initfile_name = '%s.conf' % project_name
    transform_module = '%s_transforms' % project_name
    service_module = '%s_services' % project_name
    logfile_name = '%s.log' % project_name
    project_home_dir = args.get('<project_directory>')
    if not project_home_dir:
        project_home_dir = os.getcwd()

    template_data = { 'transform_module': transform_module,
                      'service_module': service_module,
                      'logfile_name': logfile_name,
                      'project_home': project_home_dir.rstrip(os.sep) }

    j2env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'))
    template_mgr = common.JinjaTemplateManager(j2env)
    initfile_template = template_mgr.get_template('snap.conf.j2')
    print initfile_template.render(template_data)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
