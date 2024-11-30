import os
import sys
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

HYDRA_PATH: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def deploy_hydra(roles, fault_latency_us=30):
    """Deploy Hydra"""
    # get infiniband IP address for each hydra server
    ibip = Command(cmd = "ip -o -4 address show | grep eth | awk '$4 ~ /^10.10/ { print $4 }'", nodes = roles['hydra'])
    ibip.deploy()
    extra_vars = ibip.stdout_to_dict('ibip')

    # install hydra
    extra_vars.update({
        "enos_action": "deploy",
        "hydra_home": HYDRA_PATH,
    })
    _playbook = os.path.join(HYDRA_PATH, "ansible", "hydra.yml")
    r = run_ansible([_playbook], roles=roles, extra_vars=extra_vars)

    # deploy resource monitor
    cmd = f"{HYDRA_PATH}/resource_monitor/resource_monitor {{{{ hostvars[inventory_hostname]['ibip'][inventory_hostname] }}}} 9400"
    resource_monitor = Session(Command(cmd), session = "resource_monitor", nodes = roles['monitor'], extra_vars = extra_vars)
    resource_monitor.deploy()
    resource_monitor.output()

    # deploy resilience manager
    cmd = f"{HYDRA_PATH}/setup/resilience_manager_setup.sh"
    resilience_manager = Command(cmd, nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True, extra_vars = extra_vars)
    resilience_manager.deploy()
    resilience_manager.output()

def destroy_hydra(roles):
    """Destroy Hydra"""
    # get infiniband IP address for each hydra server
    ibip = Command(cmd = "ip -o -4 address show | grep eth | awk '$4 ~ /^10.10/ { print $4 }'", nodes = roles['hydra'])
    ibip.deploy()
    extra_vars = ibip.stdout_to_dict('ibip')

    # install hydra
    extra_vars.update({
        "enos_action": "destroy",
        "hydra_home": HYDRA_PATH,
    })
    _playbook = os.path.join(HYDRA_PATH, "ansible", "hydra.yml")
    r = run_ansible([_playbook], roles=roles, extra_vars=extra_vars)

    # destroy resilience manager
    cmd = f"{HYDRA_PATH}/setup/resilience_manager_teardown.sh"
    resilience_manager = Command(cmd, nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True, extra_vars = extra_vars)
    resilience_manager.deploy()
    resilience_manager.output()

    # destroy resource monitor
    cmd = f"{HYDRA_PATH}/resource_monitor/resource_monitor {{{{ hostvars[inventory_hostname]['ibip'][inventory_hostname] }}}} 9400"
    resource_monitor = Session(Command(cmd), session = "resource_monitor", nodes = roles['monitor'], extra_vars = extra_vars)
    resource_monitor.destroy()

def set_fault_injection_enable(roles, val):
    manager_alias = roles['manager'][0].alias

    # set fault injection
    cmd = f"echo {val} | tee /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_enable"
    fault_injection_enable = Command(cmd, nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True)
    fault_injection_enable.deploy()

    # validate fault injection
    cmd = f"cat /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_enable"
    fault_injection_enable = Command(cmd, nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True)
    fault_injection_enable.deploy()
    stdout = fault_injection_enable.stdout_to_dict('key')['key']
    assert(int(stdout[manager_alias]) == val)

def enable_fault_injection(roles, fault_rate = 1000):
    manager_alias = roles['manager'][0].alias

    # configure fault injection distribution
    cmd = f"echo {fault_rate} | tee /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_distr"
    fault_injection_distr = Command(cmd, nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True)
    fault_injection_distr.deploy()

    # validate fault injection distribution
    cmd = f"cat /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_distr"
    fault_injection_distr = Command(cmd, nodes = roles['manager'], remote_working_dir = os.path.join(HYDRA_PATH, "setup"), sudo = True)
    fault_injection_distr.deploy()
    stdout = fault_injection_distr.stdout_to_dict('key')['key']
    assert(int(stdout[manager_alias]) == fault_rate)

    set_fault_injection_enable(roles, 1)

def disable_fault_injection(roles):
    manager_alias = roles['manager'][0].alias
    set_fault_injection_enable(roles, 0)

def deploy_memcached(roles, cgroup = True, mc_mem = 1024, cgroup_mem = 256):
    mem_limit_in_bytes = cgroup_mem * 1024 * 1024
    if cgroup:
        memcached = Session(Cgroup(Memcached(mc_mem), mem_limit_in_bytes), session = "memcached", nodes = roles['manager'])
    else:
        memcached = Session(Memcached(mc_mem), session = "memcached", nodes = roles['manager'])
    memcached.deploy()
    memcached.output()

def destroy_memcached(roles, cgroup = True, mc_mem = 1024, cgroup_mem = 256):
    mem_limit_in_bytes = cgroup_mem * 1024 * 1024
    if cgroup:
        memcached = Session(Cgroup(Memcached(mc_mem), mem_limit_in_bytes), session = "memcached", nodes = roles['manager'])
    else:
        memcached = Session(Memcached(mc_mem), session = "memcached", nodes = roles['manager'])
    memcached.destroy()

def run_single(roles, records=3000000, qps=1000000, time=30, fault_rate=0):
    # prepare memcached
    memcached_server = roles["manager"][0].address
    memcache_perf = MemcachePerf(master = roles['control'][0], workers = roles['workload'], threads=10, connections=1, measure_depth=1, measure_connections=1)
    memcache_perf.destroy()
    memcache_perf.deploy()
    memcache_perf.run_bench(server = memcached_server, load=True, records=records, iadist = "fb_ia", keysize = "fb_key", valuesize = "fb_value")

    results = memcache_perf.run_bench(server = memcached_server, load=False, records=records, iadist = "fb_ia", keysize = "fb_key", valuesize = "fb_value", qps=qps, time=time)
    memcache_perf.destroy()
    return results


def run_multiple(roles, root_results_dir_path, batch_name, iterations=1, records=3000000, time=30):
    results_dir_path = os.path.join(root_results_dir_path, batch_name)
    if not os.path.exists(results_dir_path):
        os.makedirs(results_dir_path)

    fault_rate = 0
    for iteration in range(iterations):
        for qps in [1000, 10000, 100000, 200000, 400000, 800000, 1000000]:
            results = run_single(roles, records, qps, time, fault_rate)
            results_file_name = "qps={}-fault_rate={}-{}".format(qps, fault_rate, iteration)
            results_path_name = os.path.join(results_dir_path, results_file_name)
            with open(results_path_name, 'w') as fo:
                print(results, file=fo)

def main(argv):
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
        .add_machine(roles=["hydra", "monitor"],
                    address="node4",
                    alias="static-4",
                    user="hvolos01")\
        .add_machine(roles=["hydra", "monitor"],
                    address="node5",
                    alias="static-5",
                    user="hvolos01")\
        .add_machine(roles=["hydra", "monitor"],
                    address="node6",
                    alias="static-6",
                    user="hvolos01")\
        .add_machine(roles=["workload"],
                    address="workload-node0",
                    alias="static-7",
                    user="hvolos01")\
        .add_machine(roles=["workload"],
                    address="workload-node1",
                    alias="static-8",
                    user="hvolos01")\
        .add_machine(roles=["control"],
                    address="control-node",
                    alias="static-9",
                    user="hvolos01")\
        .finalize()

    provider = Static(conf)

    roles, networks = provider.init()

    if argv[1] == "deploy_hydra":
        deploy_hydra(roles)

    if argv[1] == "destroy_hydra":
        destroy_hydra(roles)

    if argv[1] == "enable_fault_injection":
        enable_fault_injection(roles)

    if argv[1] == "disable_fault_injection":
        disable_fault_injection(roles)

    if argv[1] == "deploy_memcached":
        deploy_memcached(roles)

    if argv[1] == "destroy_memcached":
        destroy_memcached(roles)

    if argv[1] == "run_single":
        run_single(roles, 1000, 1000000, 30, 0)

    if argv[1] == "run_single_big":
        run_single(roles, 3000000, 10000, 30, 0)

    if argv[1] == "run_multiple":
        batch_name = argv[2]
        run_multiple(roles, '/users/hvolos01/data', batch_name, 10, 3000000, 60)

if __name__ == "__main__":
    main(sys.argv)
