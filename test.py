import os
import logging
from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.infra.enos_static.provider import Static
from enoslib.infra.enos_static.configuration import Configuration

from enoslib.config import config_context, set_config

from enoslib.objects import Host, PathLike

from memcached import Memcached

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

memcached = Memcached(nodes = roles['manager'], mem = 256)
# memcached.prepare()
# memcached.deploy()
memcached.destroy()


# with en.actions(roles=roles) as p:
#   p.copy(
#         dest="~/test1",
#         content="TEST1",
#         task_name="test1"
#     )
#   p.copy(
#         dest="~/test2",
#         content="TEST2",
#         task_name="test2"
#     )
#   p.copy(
#         dest="~/test3",
#         content="TEST3",
#         task_name="test3"
#     )
