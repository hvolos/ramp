from typing import Dict, Iterable, List, Optional

import enoslib as en

from enoslib.api import actions

from enoslib.api import bg_start, bg_stop

from enoslib.objects import Host, PathLike, Roles

MCPERF_SESSION = "__enoslib_mcperf__"

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

    def deploy_actions(self):
        a = actions()
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
        workers: Optional[Iterable[Host]] = None,
        threads: int = 1,
        connections: int = 1,
        measure_depth: int = 1,
        measure_connections: int = 1,
        environment: Optional[Dict] = None,        
        priors: Optional[List[actions]] = None,
        extra_vars: Optional[Dict] = None,        
    ):
        """Deploy memcache-perf.

        Args:
          nodes: the nodes to install memcached on
        """
        self.master = master
        self.workers = workers if workers is not None else []
        self.threads = threads
        self.connections = connections
        self.measure_depth = measure_depth 
        self.measure_connections = measure_connections
        self.priors = priors
        self.extra_vars = extra_vars if extra_vars is not None else {}

        self.roles = Roles()
        self.roles.update(master=[self.master], worker=self.workers)

        self.environment = environment if environment is not None else {}

        self.memcache_perf_path = "~/memcache-perf"
        self.repo = "https://github.com/shaygalon/memcache-perf.git"
        self.version = "4be8194"

    def _prepare(self):
        """Installs the memcache perf dependencies."""
        with actions(
            pattern_hosts="all",
            roles=self.roles,
            priors=self.priors,
            extra_vars=self.extra_vars,
        ) as p:
            p.apt(
                task_name="Installing memcache-perf dependencies",
                name=["libevent-dev", "libzmq3-dev"],
                state="present",
                become="yes", become_user="root"
            )
            p.git(
                task_name="Cloning memcache-perf source repository",
                repo = self.repo,
                dest = self.memcache_perf_path,
                version = self.version
            )
            p.shell(
                task_name = "Building memcache-perf",
                cmd = "cd {} && make -j4".format(self.memcache_perf_path), 
            )

    def _run_workers(self):
        environment: Dict = dict(**self.environment)
        with actions(
            pattern_hosts="worker", roles=self.roles, extra_vars=self.extra_vars
        ) as p:
            cmd = (
                f"{self.memcache_perf_path}/mcperf "
                f"--threads={self.threads} "
                "--agentmode"
                # "--agentmode 1> /tmp/out 2>&1 &"
            )
            print(bg_start(MCPERF_SESSION, cmd))
            p.shell(
                bg_start(MCPERF_SESSION, cmd),
                environment=environment,
                task_name=f"Running memcache-perf on agents...",
            )

    def deploy(self):
        """Install and run memcache-perf on the nodes."""
        self._prepare()
        self._run_workers()

    def destroy(self):
        """Stop memcache-perf."""
        with actions(
            pattern_hosts="all", roles=self.roles, extra_vars=self.extra_vars
        ) as p:
            kill_cmd = bg_stop(MCPERF_SESSION)
            p.shell(kill_cmd)

    def run_bench(
        self,
        *,
        server: str,
        load: bool,
        records: int,
        iadist: str,
        keysize: str,
        valuesize: str, 
        qps: int, 
        time: int
    ):
        workers = self.roles["worker"]
        workers_list = ["-a " + w.address for w in workers]
        workers_parameter = ' '.join(workers_list)

        load_flag = "--loadonly" if load else "--noload" 
        cmd = (
            f"{self.memcache_perf_path}/mcperf "
            f"-s {server} "
            f"{load_flag} "
            f"--blocking --threads {self.threads} -D {self.measure_depth} -C {self.measure_connections} "
            f"{workers_parameter} "
            f"-c {self.connections} "
            f"-r {records} -q {qps} -t {time} "
            f"--iadist={iadist} --keysize={keysize} --valuesize={valuesize}"
        )
        print(cmd)
        with actions(
            pattern_hosts="master", roles=self.roles, extra_vars=self.extra_vars
        ) as p:
            p.shell(
                cmd,
                task_name=f"Running memcache-perf on master...",
            )
            results = p.results
        print(results)