import logging
import os
import signal

from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

logger = logging.getLogger()

from rich.console import Console

from rich import print as rprint


def cgroup_start(cgroup_controller: str, cgroup_path:str, cmd: str) -> str:
    """Put a command in the background.

    Generate the command that will put cmd in background.
    This uses tmux to detach cmd from the current shell session.

    Idempotent

    Args:
        cmd: the command to put in background

    Returns:
        command encapsulated in a tmux session identified by the key

    """
    # supports templating
    return f"cgexec -g {cgroup_controller}:{cgroup_path} {cmd}"

class Cgroup:
    def __init__(
        self,
        child: str,
        *,
        # nodes: Iterable[Host],
        remote_working_dir: str = None,
        extra_vars: Optional[Dict] = None,
    ):
        """Deploy dstat on all hosts.

        This assumes a debian/ubuntu based environment and aims at producing a
        quick way to deploy a simple monitoring stack based on dstat on your nodes.
        It's opinionated out of the box but allow for some convenient customizations.

        Args:
            nodes: the nodes to install dstat on
            priors : priors to apply
            remote_working_dir: remote working directory
            extra_vars: extra vars to pass to Ansible

        """
        self.child = child
        self.cgroup_controller = "memory"
        self.cgroup_path = "memctl"
        self.user = "hvolos01"
        self.memlimit = 256
        # self.nodes = nodes
        # self.options = options
        # make it unique per instance
        # identifier = str(time_ns())

        # make it unique per instance
        # self.backup_dir = _set_dir(backup_dir, LOCAL_OUTPUT_DIR / identifier)

        # self.output_file = f"{identifier}-{OUTPUT_FILE}"

        self.extra_vars = extra_vars if extra_vars is not None else {}
    
    def deploy(self):
        """Deploy the session."""
        a = en.actions()        
        a.apt(
            task_name="Checking cgroup dependencies",
            name=["cgroup-bin", "cgroup-lite", "libcgroup1"],
            state="present",
            when="ansible_distribution == 'Ubuntu' and ansible_distribution_version == '14.04'",
            become="yes", become_user="root"
        )
        a.shell(
            f"cgcreate -t {self.user} -a {self.user} -g {self.cgroup_controller}:{self.cgroup_path}",
            task_name="Create cgroup {self.cgroup_controller}:{self.cgroup_path}",
            become="yes", become_user="root"
        )
        dest = os.path.join("/sys/fs/cgroup", self.cgroup_controller, self.cgroup_path, "memory.limit_in_bytes")
        a.shell(
            f"echo {self.memlimit}m > {dest}"
        )

        # Collect the child actions for execution. 
        # Ensure the last child action is a shell task and modify it to enclose it 
        # within a cgexec command.
        child_actions = self.child.deploy()
        last_child_action = child_actions._tasks.pop()
        assert 'shell' in last_child_action

        last_child_cmd = last_child_action['shell']
        child_actions.shell(
            cgroup_start(self.cgroup_controller, self.cgroup_path, f"{last_child_cmd}"),
            task_name=f"Running {last_child_cmd} in a tmux session",
        )

        return en.actions(priors = [a, child_actions])

    def destroy(self):
        """Destroy the session.

        This kills the session processes on the nodes.
        """
        with en.actions(roles=self.nodes, extra_vars=self.extra_vars) as p:
            kill_cmd = bg_stop(self.session)
            p.shell(kill_cmd, task_name="Killing existing session")

    def output(self):
        results = en.run_command(bg_capture(self.session), roles = self.nodes)
        for result in results:
            host = result.host
            for line in result.payload['stdout_lines']:
                rprint(f"[red]{host}[/red]\t{line}")
        