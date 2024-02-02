import os
import logging
from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.api import run_ansible
from enoslib.infra.enos_static.provider import Static
from enoslib.infra.enos_static.configuration import Configuration

from enoslib.config import config_context, set_config

from enoslib.objects import Host, PathLike

from memcached import Memcached
from session import Session

en.init_logging(level=logging.INFO)

# path to the inventory
inventory = os.path.join(os.getcwd(), "hosts")

# claim the resources
conf = Configuration.from_settings()\
    .add_machine(roles=["manager"],
                 address="node0",
                 alias="static-0",
                 user="hvolos01")\
    .add_machine(roles=["monitor"],
                 address="node1",
                 alias="static-1",
                 user="hvolos01")\
    .add_machine(roles=["monitor"],
                 address="node2",
                 alias="static-2",
                 user="hvolos01")\
    .add_machine(roles=["monitor"],
                 address="node3",
                 alias="static-3",
                 user="hvolos01")\
    .finalize()

provider = Static(conf)

roles, networks = provider.init()

def register_command_stdout_to_variable(var, cmd, nodes):
    d = {}
    results = en.run_command(cmd, roles = nodes, task_name = f"Register { cmd } stdout to variable {var}")
    for result in results:
        if result.status == 'OK':
            d[result.host] = result.stdout
    return {var: d}

extra_vars = register_command_stdout_to_variable(var = 'ibip', cmd = "ip -o -4 address show | awk '$4 ~ /^10.10/ { print $4 }'", nodes = roles)

HYDRA_PATH: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def deploy_hydra(roles):
    """Deploy Hydra"""
    extra_vars = {
        "enos_action": "deploy",
        "hydra_home": HYDRA_PATH,
        # "collector_address": get_address(self.collector, self.networks),
        # "collector_port": collector_port,
        # "collector_env": self.collector_env,
        # "collector_type": "influxdb",
        # "agent_conf": self.agent_conf,
        # "agent_image": self.agent_image,
        # "remote_working_dir": self.remote_working_dir,
        # "ui_address": ui_address,
        # "ui_port": self.ui_env["GF_SERVER_HTTP_PORT"],
        # "ui_env": self.ui_env,
    }
    extra_vars.update(extra_vars)
    _playbook = os.path.join(HYDRA_PATH, "ansible", "hydra.yml")
    r = run_ansible([_playbook], roles=roles, extra_vars=extra_vars)
    print(r)

# deploy_hydra(roles)

# result = en.gather_facts(roles=roles)

cmd = f"{HYDRA_PATH}/resource_monitor/resource_monitor {{{{ hostvars[inventory_hostname]['ibip'][inventory_hostname] }}}} 9400"
session = Session(cmd = cmd, session = "resource_monitor", nodes = roles['monitor'], extra_vars = extra_vars)

session.deploy()

session.output()

# memcached = Memcached(nodes = roles['manager'], mem = 256)
# memcached.prepare()
# memcached.deploy()
# memcached.destroy()