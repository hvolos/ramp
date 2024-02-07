import logging
import signal

from typing import Dict, Iterable, Optional

import enoslib as en

from enoslib.objects import Host, PathLike

logger = logging.getLogger()

from rich.console import Console

from rich import print as rprint


def bg_start(key: str, cmd: str) -> str:
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


def bg_stop(key: str, num: int = signal.SIGINT) -> str:
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

def bg_capture(key: str) -> str:
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

class Session:
    def __init__(
        self,
        child: str,
        *,
        session: str,
        nodes: Iterable[Host],
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
        self.session = session
        self.nodes = nodes
        # self.options = options
        # make it unique per instance
        # identifier = str(time_ns())
        self.remote_working_dir = remote_working_dir

        # make it unique per instance
        # self.backup_dir = _set_dir(backup_dir, LOCAL_OUTPUT_DIR / identifier)

        # self.output_file = f"{identifier}-{OUTPUT_FILE}"

        self.extra_vars = extra_vars if extra_vars is not None else {}
    
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
        child_actions.shell(
            bg_start(self.session, f"{last_child_cmd}"), 
            task_name=f"Running {last_child_cmd} in a tmux session",
            **shell_kwargs
        ) 
        print(bg_start(self.session, f"{last_child_cmd}"))     

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
            kill_cmd = bg_stop(self.session)
            p.shell(kill_cmd, task_name="Killing existing session")

    def output(self):
        results = en.run_command(bg_capture(self.session), roles = self.nodes)
        for result in results:
            host = result.host
            for line in result.payload['stdout_lines']:
                rprint(f"[red]{host}[/red]\t{line}")
        