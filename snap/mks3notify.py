#!/usr/bin/env python

'''Usage: mks3notify (sns | sqs) --name=<config_name> --arn=<target_arn>

'''

import docopt
import jinja2
import common


templates = {
'sns': 's3_sns_notify_config.xml.j2',
'sqs': 's3_sqs_notify_config.xml.j2'
}


NotifierTargetType = common.Enum(['sns', 'sqs'])

class S3Event(object):
    @staticmethod
    def object_created_put():
        return 's3:ObjectCreated:Put'

    @staticmethod
    def object_created_post():
        return 's3:ObjectCreated:Post'

    @staticmethod
    def object_created_any():
        return 's3:ObjectCreated:*'


class TopicConfig(object):
    def __init__(self, id, filter_rules, events):
        pass


class NotificationConfigBuilder(object):
    def __init__(self, target_type, config_name, notification_target_arn, template_mgr):
        self.name = config_name
        self.filter_rules = []
        self.events = []
        self.target_type = target_type
        self.target_arn = notification_target_arn
        self.template_mgr = template_mgr


    def add_filter_rule(self, name, value):
        self.filter_rules.append({'name': name, 'value': value})
        return self


    def add_event(self, event_type):
        self.events.append(event_type)
        return self


    def build(self):
        config_data = dict(id=self.name, 
                           target_arn=self.target_arn, 
                           rules=self.filter_rules, 
                           events=self.events)

        template_name = templates.get(self.target_type)
        if not template_name:
            raise Exception('Notification type "%s" is not supported.' % self.target_type)
        template = self.template_mgr.get_template(template_name)
        return template.render(config_data)


def mk_sqs_config(config_name, aws_queue_id, template_mgr):
    data = NotificationConfigBuilder(config_name, 
                              aws_queue_id).add_event(S3Event.object_created_any()).build()

    template = template_mgr.get_template(templates['sqs'])
    return template.render(data)
    

def mk_sns_config(config_name, aws_topic_id, template_mgr):
    data = NotificationConfigBuilder(config_name, 
                              aws_topic_id).add_event(S3Event.object_created_any()).build()

    template = template_mgr.get_template(templates['sns'])
    return template.render(data)

    

def main(args):
    j2env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'))
    tmgr = common.JinjaTemplateManager(j2env)

    config_name = args['--name']
    target_arn = args['--arn']

    if args['sns']:
        builder = NotificationConfigBuilder('sns',
                                            config_name, 
                                            target_arn,
                                            tmgr).add_event(S3Event.object_created_any())
    else:
        builder = NotificationConfigBuilder('sqs',
                                            config_name,
                                            target_arn,
                                            tmgr).add_event(S3Event.object_created_any())

    print builder.build()
    
        

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
