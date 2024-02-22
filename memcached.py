from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

class Memcached(en.service.service.Service):
    def __init__(
        self, 
        mem: int
    ):
        """Deploy memcached on all hosts.

        Args:
          nodes: the nodes to install memcached on
        """
        self.mem = mem
        self.memcached_path = "~/memcached"
        self.repo = "https://github.com/memcached/memcached.git"
        self.version = "1.6.12"

    def deploy(self):
        a = en.actions()
        a.apt(
          name=["libevent-dev"],
          state="present",
          become="yes", become_user="root"
        )
        a.git(
          repo = self.repo,
          dest = self.memcached_path,
          version = self.version
        )
        a.shell("cd {} && ./autogen.sh && ./configure && make -j4".format(self.memcached_path), 
                task_name = "Build memcached")
        a.shell(f"{self.memcached_path}/memcached -m {self.mem}", task_name = "Run memcached")
        return a


class MemcachePerf(en.service.service.Service):
    def __init__(
        self, 
        # deployment options
        master: Host,
        workers: Optional[Iterable[Host]] = None
    ):
        """Deploy memcached on all hosts.

        Args:
          nodes: the nodes to install memcached on
        """
        self.mem = mem
        self.memcached_path = "~/memcached"
        self.repo = "https://github.com/shaygalon/memcache-perf.git"
        self.version = "1.6.12"

    def deploy(self):
        a = en.actions()
        a.apt(
            name=["libevent-dev"],
            state="present",
            become="yes", become_user="root"
        )
        a.git(
            repo = self.repo,
            dest = self.memcached_path,
            version = self.version
        )
