#!/usr/bin/env python

'''Usage: mks3notify (sns | sqs)

'''

import docopt
import jinja2
import common


templates = {
'sns': 's3_sns_notify_config.xml.j2',
'sqs': 's3_sqs_notify_config.xml.j2'
}



class S3Event(object):
    @staticmethod
    def object_created_put():
        return 's3:ObjectCreated:Put'

    @staticmethod
    def object_created_Post():
        return 's3:ObjectCreated:Post'

    @staticmethod
    def object_created_any():
        return 's3:ObjectCreated:*'


class TopicConfig(object):
    def __init__(self, id, filter_rules, events):
        pass


class TopicConfigBuilder(object):
    def __init__(self, id_string, amazon_resource_num):
        self.id = id_string
        self.filter_rules = []
        self.events = []
        self.target_arn = amazon_resource_num

    def add_filter_rule(self, name, value):
        self.filter_rules.append({'name': name, 'value': value})
        return self

    def add_event(self, event_type):
        self.events.append(event_type)
        return self

    def build(self):
        return dict(id=self.id, 
                    arn=self.target_arn, 
                    rules=self.filter_rules, 
                    events=self.events)



def mk_sns_config(topic_name, aws_resource_id, template_mgr):
    data = TopicConfigBuilder(topic_name, aws_resource_id).add_event(S3Event.object_created_any()).build()

    template = template_mgr.get_template(templates['sns'])
    print template.render(data)
    


def mk_sqs_config():
    pass



def main(args):
    #print args

    j2env = jinja2.Environment(loader = jinja2.FileSystemLoader('templates'))
    tmgr = common.JinjaTemplateManager(j2env)
    

    if args['sns']:
        print mk_sns_config('test', 'arn::dummy', tmgr)
    
        

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
