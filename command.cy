import logging
import signal

from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

logger = logging.getLogger()

from rich.console import Console

from rich import print as rprint

class Command:
  def __init__(
    self, 
    cmd: str):
    """Run command on all hosts.

    Args:
      cmd: the command to run
    """
    self.cmd = cmd

  def deploy_actions(self):
    a = en.actions()
    a.shell(self.cmd) 
    return a

  def deploy(self):
    a = self.deploy_actions()
    with en.actions(
        roles=self.nodes, extra_vars=self.extra_vars, gather_facts=True, 
        priors = [a]
    ) as p:
        results = p.results
        pass


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
        child_actions = self.child.deploy()
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
        