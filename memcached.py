from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

class Memcached(en.service.service.Service):
  def __init__(
    self, 
    nodes: Iterable[Host],
    mem: int):
    """Deploy memcached on all hosts.

    Args:
      nodes: the nodes to install memcached on
    """
    self.nodes = nodes
    self.mem = mem
    self.memcached_path = "~/memcached"
    self.repo = "https://github.com/memcached/memcached.git"
    self.version = "1.6.12"

    self.cmd = f"{self.memcached_path}/memcached} -m {self.mem}"

  def deploy_actions(self, p):
    p.apt(
      name=["libevent-dev"],
      state="present",
    )
    p.git(
      repo = self.repo,
      dest = self.memcached_path,
      version = self.version
    )
    p.shell("cd {} && ./autogen.sh && ./configure && make -j4".format(self.memcached_path))

