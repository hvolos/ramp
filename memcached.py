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

  def _install_dependencies(self):
    with en.actions(roles=self.nodes, run_as="root") as p:
      p.apt(
          name=["supervisor", "libevent-dev"],
          state="present",
      )

  def prepare(self):
    self._install_dependencies()        
    with en.actions(roles=self.nodes) as p:
      p.git(
              repo = self.repo,
              dest = self.memcached_path,
              version = self.version
          )
      p.shell("cd {} && ./autogen.sh && ./configure 2>&1 && make -j4".format(self.memcached_path))
      results = p.results

  def deploy(self):
    with en.actions(roles=self.nodes) as p:
      p.shell(
          (
              f"nohup {self.memcached_path}/memcached "
              f"-m {self.mem} &"
          ),
          task_name=f"Running memcached ({self.memcached_path})",
      )

  def destroy(self):
    """Stop memcached."""
    for node in self.nodes:
      print(node)
    with en.actions(roles=self.nodes) as p:
      p.shell("if pgrep memcached; then pkill memcached; fi", 
              task_name=f"Killing memcached")
