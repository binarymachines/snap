


import os
import json
from tempfile import NamedTemporaryFile
import ansible
from ansible.inventory import Inventory
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor import playbook_executor
from ansible.utils.display import Display
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase



DEFAULT_OPTIONS_TBL = dict(
    verbosity=None,
    inventory=None,
    listhosts=None,
    subset=None,
    module_paths=None,
    extra_vars=None,    
    forks=100,
    ask_vault_pass=None,
    vault_password_files=None,
    new_vault_password_file=None,
    output_file=None,
    tags=None,
    skip_tags=None,
    one_line=None,
    tree=None,
    ask_sudo_pass=None,
    ask_su_pass=None,
    sudo=None,
    sudo_user=None,
    become=None,
    become_method=None,
    become_user=None,
    become_ask_pass=None,
    ask_pass=None,
    private_key_file=None,
    remote_user=None,
    connection='local',
    timeout=None,
    ssh_common_args=None,
    sftp_extra_args=None,
    scp_extra_args=None,
    ssh_extra_args=None,
    poll_interval=None,
    seconds=None,
    check=False,
    syntax=None,
    diff=None,
    force_handlers=None,
    flush_cache=None,
    listtasks=None,
    listtags=None,
    module_path=None
)

DEFAULT_OPTION_NAMES = DEFAULT_OPTIONS_TBL.keys()

class DefaultOptions(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

                
class Options(DefaultOptions):
    """
    Options class to replace Ansible OptParser
    """
    def __init__(self, **kwargs):
        DefaultOptions.__init__(self, **DEFAULT_OPTIONS_TBL)
        for key, value in kwargs.iteritems():
            setattr(self, key, value)



class DefaultResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """
    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        print json.dumps({host.name: result._result}, indent=4)




class PlaySourceBuilder(object):
    def __init__(self):
        self.tasks = []


    def add_task(self, module_name, module_args, register='shell_out', **kwargs):
        new_task = dict(action = dict(module=module_name, args=module_args), register=register)
        self.tasks.append(new_task)

        return self

    def build(self):
        return dict(
            name = 'Ansible Play from Snap ansiblex',
            hosts = 'localhost',
            gather_facts = 'no',
            tasks = self.tasks            
        )        

    
class AnsibleContext(object):
    def __init__(self, **kwargs):
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.options = Options(**kwargs)
        self.default_results_callback = DefaultResultCallback()
        self.inventory = Inventory(loader = self.loader, variable_manager = self.variable_manager, host_list='localhost')
        self.variable_manager.set_inventory(self.inventory)


    def execute_play(self, play_source):
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)
        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords={},
                stdout_callback=self.default_results_callback 
            )
            result = tqm.run(play)

            print 'executed playbook, terminated with code %d.' % result
        
        finally:
            if tqm is not None:
                tqm.cleanup()
                
        

