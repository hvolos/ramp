import logging
import os
import signal

from typing import Dict, Iterable, List, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

logger = logging.getLogger()

from rich.console import Console

from rich import print as rprint


class _MemoryCgroup:
    def __init__(
        self,
        cgroup_path: str,
        limit_in_bytes: int
    ):
        self.cgroup_controller = "memory"
        self.cgroup_path = cgroup_path
        self.limit_in_bytes = limit_in_bytes

    def controller_path_pair(self):
        return f"{self.cgroup_controller}:{self.cgroup_path}"

    def parameter_path(self, parameter_name: str):
        return os.path.join("/sys/fs/cgroup", self.cgroup_controller, self.cgroup_path, parameter_name)

    def register_deploy_actions(self, a):
        a.shell(
            f"cgcreate -t {{{{ ansible_user_id }}}} -a {{{{ ansible_user_id }}}} -g {self.controller_path_pair()}",
            task_name=f"Create cgroup {self.controller_path_pair()}",
            become="yes", become_user="root"
        )
        a.shell(
            f"echo {self.limit_in_bytes} > {self.parameter_path('memory.limit_in_bytes')}"
        )


class Cgroup:
    def __init__(
        self,
        child: str,
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
        self.memory_cgroup = _MemoryCgroup(cgroup_path = "memctl", limit_in_bytes = 256*1024*1024)

    def _cgexec(cgroup_controller_path_pairs: List[str], cmd: str) -> str:
        """Put a command in the background.

        Generate the command that will put cmd in background.
        This uses tmux to detach cmd from the current shell session.

        Idempotent

        Args:
            cmd: the command to put in background

        Returns:
            command encapsulated in a tmux session identified by the key

        """
        cgroup_controller_path_pair_str = ' '.join([f"-g {pair}" for pair in cgroup_controller_path_pairs])
        return f"cgexec {cgroup_controller_path_pair_str} {cmd}"


    def deploy(self):
        """Deploy the cgroup."""
        a = en.actions()        
        a.apt(
            task_name="Checking cgroup package dependencies",
            name=["cgroup-bin", "cgroup-lite", "libcgroup1"],
            state="present",
            when="ansible_distribution == 'Ubuntu' and ansible_distribution_version == '14.04'",
            become="yes", become_user="root"
        )

        self.memory_cgroup.register_deploy_actions(a)
        cgroup_controller_path_pairs = [self.memory_cgroup.controller_path_pair()]

        # Collect the child actions for execution. 
        # Ensure the last child action is a shell task and modify it to enclose it 
        # within a cgexec command.
        child_actions = self.child.deploy()
        last_child_action = child_actions._tasks.pop()
        assert 'shell' in last_child_action

        last_child_cmd = last_child_action['shell']
        child_actions.shell(
            self._cgexec(cgroup_controller_path_pairs, f"{last_child_cmd}"),
            task_name=f"Running {last_child_cmd} in a cgroup",
        )

        return en.actions(priors = [a, child_actions])

    def destroy(self):
        """Destroy the cgroup."""
        a = en.actions()        
            kill_cmd = bg_stop(self.session)
            p.shell(kill_cmd, task_name="Killing existing session")
