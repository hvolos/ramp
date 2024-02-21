import logging
import signal

from typing import List, Dict, Iterable, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

logger = logging.getLogger()

from rich.console import Console

from rich import print as rprint

class Command:
    def __init__(
        self, 
        cmd: str,
        nodes: Iterable[Host],
        remote_working_dir: str = None,
        sudo: bool = False, 
        extra_vars: Optional[Dict] = None,
    ):
        """Run command on all hosts.

        Args:
            cmd: the command to run
        """
        self.cmd = cmd
        self.nodes = nodes
        self.remote_working_dir = remote_working_dir
        self.sudo = sudo
        self.extra_vars = extra_vars
        self.results = None

    def deploy_actions(self):
        a = en.actions()
        shell_kwargs = {}
        if self.remote_working_dir:
            shell_kwargs['chdir'] = str(self.remote_working_dir)
        if self.sudo:
            shell_kwargs['become'] = "yes"
            shell_kwargs['become_user'] = "root"
        a.shell(self.cmd, **shell_kwargs) 
        return a

    def deploy(self):
        a = self.deploy_actions()
        with en.actions(
            roles=self.nodes, extra_vars=self.extra_vars, gather_facts=True, 
            priors = [a]
        ) as p:
            self.results = p.results

    def stdout_to_variable(self, var):
        """Returns a dictionary with standard output assigned to a variable

        Args:
            child: the variable
        """
        d = {}
        for result in self.results:
            print(result)
            # if result.status == 'OK':
            #     d[result.host] = result.stdout
        return {var: d}


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
        """Run a command in a control group

        Args:
            child: the command to run in a control group
        """
        self.child = child
        self.memory_cgroup = _MemoryCgroup(cgroup_path = "memctl", limit_in_bytes = 256*1024*1024)

    def _cgexec(cgroup_controller_path_pairs: List[str], cmd: str) -> str:
        """Run a command in a given control group

        Generate the command that will run a command in a given control group.

        Args:
            cmd: the command to run in a control group

        Returns:
            command encapsulated in a a cgexec session

        """
        cgroup_controller_path_pair_str = ' '.join([f"-g {pair}" for pair in cgroup_controller_path_pairs])
        return f"cgexec {cgroup_controller_path_pair_str} {cmd}"


    def deploy_actions(self):
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
        child_actions = self.child.deploy_actions()
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


class Session:
    def __init__(
        self,
        child: str,
        *,
        session: str,
        nodes: Iterable[Host],
        remote_working_dir: str = None,
        sudo: bool = False, 
        extra_vars: Optional[Dict] = None,
    ):
        """Run a command in the background.

        Args:
            child: the command to run in the background
            nodes: the nodes to run the command on
            remote_working_dir: remote working directory
            extra_vars: extra vars to pass to Ansible

        """
        self.child = child
        self.session = session
        self.nodes = nodes
        # self.options = options
        # make it unique per instance
        # identifier = str(time_ns())
        self.remote_working_dir = remote_working_dir
        self.sudo = sudo 

        # make it unique per instance
        # self.backup_dir = _set_dir(backup_dir, LOCAL_OUTPUT_DIR / identifier)

        # self.output_file = f"{identifier}-{OUTPUT_FILE}"

        self.extra_vars = extra_vars if extra_vars is not None else {}

    @staticmethod
    def _bg_start(key: str, cmd: str) -> str:
        """Put a command in the background.

        Generate the command that will put cmd in background.
        This uses tmux to detach cmd from the current shell session.

        Idempotent

        Args:
            key: session identifier for tmux (must be unique)
            cmd: the command to put in background

        Returns:
            command encapsulated in a tmux session identified by the key

        """
        # supports templating
        return f"(tmux ls | grep {key}) ||tmux new-session -s {key} -d '{cmd}'"

    @staticmethod
    def _bg_stop(key: str, num: int = signal.SIGINT) -> str:
        """Stop a command that runs in the background.

        Generate the command that will stop a previously started command in the
        background with :py:func:`bg_start`

        Args:
            key: session identifier for tmux.

        Returns:
            command that will stop a tmux session
        """
        if num == signal.SIGHUP:
            # default tmux termination signal
            # This will send SIGHUP to all the encapsulated processes
            return f"tmux kill-session -t {key} || true"
        else:
            # We prefer send a sigint to all the encapsulated processes
            cmd = f"(tmux list-panes -t {key} -F '#{{pane_pid}}' | xargs -n1 kill -{int(num)}) || true"  # noqa
            return cmd

    @staticmethod
    def _bg_capture(key: str) -> str:
        """Capture the output of a command that runs in the background.

        Generate the command that will collect a previously started command in the
        background with :py:func:`bg_start`

        Args:
            key: session identifier for tmux.

        Returns:
            command that will capture the output of a tmux session
        """
        cmd = f"tmux capture-pane -t {key} -p"
        return cmd


    def deploy(self):
        """Deploy the session."""
        a = en.actions()        
        a.shell(
            "which tmux || (apt update && apt install -y tmux)",
            task_name="Checking tmux",
            when="ansible_os_family == 'Debian'",
            become="yes", become_user="root"
        )

        # Collect the child actions for execution. 
        # Ensure the last child action is a shell task and modify it to enclose it 
        # within a tmux command.
        child_actions = self.child.deploy_actions()
        last_child_action = child_actions._tasks.pop()
        assert 'shell' in last_child_action

        last_child_cmd = last_child_action['shell']
        shell_kwargs = {}
        if self.remote_working_dir:
            shell_kwargs['chdir'] = str(self.remote_working_dir)
        if self.sudo:
            child_actions.shell(
                Session._bg_start(self.session, f"{last_child_cmd}"), 
                task_name=f"Running {last_child_cmd} in a tmux session",
                become="yes", become_user="root",
                **shell_kwargs)

        else:
            child_actions.shell(
                Session._bg_start(self.session, f"{last_child_cmd}"), 
                task_name=f"Running {last_child_cmd} in a tmux session",
                **shell_kwargs) 

        # Execute the actions
        with en.actions(
            roles=self.nodes, extra_vars=self.extra_vars, gather_facts=True, 
            priors = [a, child_actions]
        ) as p:
            results = p.results
            pass
        for result in results:
            print(result)

    def destroy(self):
        """Destroy the session.

        This kills the session processes on the nodes.
        """
        with en.actions(roles=self.nodes, extra_vars=self.extra_vars) as p:
            kill_cmd = Session._bg_stop(self.session)
            p.shell(kill_cmd, task_name="Killing existing session")

    def output(self):
        results = en.run_command(Session._bg_capture(self.session), roles = self.nodes)
        for result in results:
            host = result.host
            for line in result.payload['stdout_lines']:
                rprint(f"[red]{host}[/red]\t{line}")
        