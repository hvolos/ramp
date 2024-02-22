import os
import logging
from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.api import run_ansible
from enoslib.infra.enos_static.provider import Static
from enoslib.infra.enos_static.configuration import Configuration

from enoslib.config import config_context, set_config

from enoslib.objects import Host, PathLike

from memcached import Memcached, MemcachePerf
from command import Command, Cgroup, Session

en.init_logging(level=logging.INFO)

# path to the inventory
inventory = os.path.join(os.getcwd(), "hosts")

# claim the resources
conf = Configuration.from_settings()\
    .add_machine(roles=["hydra", "manager"],
                 address="node0",
                 alias="static-0",
                 user="hvolos01")\
    .add_machine(roles=["hydra", "monitor"],
                 address="node1",
                 alias="static-1",
                 user="hvolos01")\
    .add_machine(roles=["hydra", "monitor"],
                 address="node2",
                 alias="static-2",
                 user="hvolos01")\
    .add_machine(roles=["hydra", "monitor"],
                 address="node3",
                 alias="static-3",
                 user="hvolos01")\
    .add_machine(roles=["workload"],
                 address="workload-node0",
                 alias="static-4",
                 user="hvolos01")\
    .add_machine(roles=["workload"],
                 address="workload-node1",
                 alias="static-5",
                 user="hvolos01")\
    .add_machine(roles=["control"],
                 address="control-node",
                 alias="static-6",
                 user="hvolos01")\
    .finalize()

provider = Static(conf)

roles, networks = provider.init()

# ibip = Command(cmd = "ip -o -4 address show | grep eth | awk '$4 ~ /^10.10/ { print $4 }'", nodes = roles['hydra'])
# ibip.deploy()
# extra_vars = ibip.stdout_to_dict('ibip')

HYDRA_PATH: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def deploy_hydra(roles, extra_vars):
    """Deploy Hydra"""
    extra_vars.update({
        "enos_action": "deploy",
        "hydra_home": HYDRA_PATH,
    })
    _playbook = os.path.join(HYDRA_PATH, "ansible", "hydra.yml")
    r = run_ansible([_playbook], roles=roles, extra_vars=extra_vars)

# deploy_hydra(roles, extra_vars)

# cmd = f"{HYDRA_PATH}/resource_monitor/resource_monitor {{{{ hostvars[inventory_hostname]['ibip'][inventory_hostname] }}}} 9400"
# resource_monitor = Session(Command(cmd), session = "resource_monitor", nodes = roles['monitor'], extra_vars = extra_vars)
# resource_monitor.deploy()
# resource_monitor.output()

# cmd = f"{HYDRA_PATH}/setup/resilience_manager_setup.sh"
# shell_kwargs = {}
# shell_kwargs['chdir'] = os.path.join(HYDRA_PATH, "setup")
# results = en.run_command(cmd, roles = roles['manager'], task_name = f"Run { cmd }", run_as="root", extra_vars = extra_vars, **shell_kwargs)

# resilience_manager = Session(Command(cmd), session = "resilience_manager", nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True, extra_vars = extra_vars)
# resilience_manager.deploy()
# resilience_manager.output()

# memcached = Session(Memcached(mem = 256), session = "memcached", nodes = roles['manager'])
# memcached = Session(Cgroup(Memcached(mem = 256)), session = "memcached", nodes = roles['manager'])
# memcached.deploy()

# memcached_server = roles["manager"][0].address
memcached_server = "node0"
memcache_perf = MemcachePerf(master = roles['control'][0], workers = roles['workload'], threads=40)
memcache_perf.deploy()
# memcache_perf.run_bench(server = memcached_server, load=True, records=1000, iadist = "fb_ia", keysize = "fb_key", valuesize = "fb_value", qps=1000, time=10)
# memcache_perf.run_bench(server = memcached_server, load=False, records=1000, iadist = "fb_ia", keysize = "fb_key", valuesize = "fb_value", qps=1000, time=10)
# memcache_perf.destroy()


# memcached.destroy()
