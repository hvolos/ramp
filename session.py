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
        *,
        cmd: str,
        session: str,
        nodes: Iterable[Host],
        options: str = "-aT",
        extra_vars: Optional[Dict] = None,
    ):
        """Deploy dstat on all hosts.

        This assumes a debian/ubuntu based environment and aims at producing a
        quick way to deploy a simple monitoring stack based on dstat on your nodes.
        It's opinionated out of the box but allow for some convenient customizations.

        Args:
            nodes: the nodes to install dstat on
            options: options to pass to dstat.
            priors : priors to apply
            extra_vars: extra vars to pass to Ansible

        """
        self.cmd = cmd
        self.session = session
        self.nodes = nodes
        self.options = options
        # make it unique per instance
        # identifier = str(time_ns())
        # self.remote_working_dir = Path(REMOTE_OUTPUT_DIR) / identifier

        # make it unique per instance
        # self.backup_dir = _set_dir(backup_dir, LOCAL_OUTPUT_DIR / identifier)

        # self.output_file = f"{identifier}-{OUTPUT_FILE}"

        self.extra_vars = extra_vars if extra_vars is not None else {}
    
    def deploy(self):
        """Deploy the session."""

        with en.actions(
            roles=self.nodes, extra_vars=self.extra_vars, gather_facts=True
        ) as p:
            # work on system that already have tmux or fallback to the
            # installation of tmux (debian, ubuntu... only for now)
            p.shell(
                "which tmux || (apt update && apt install -y tmux)",
                task_name="Checking tmux",
                when="ansible_os_family == 'Debian'",
                become="yes", become_user="root"
            )
            p.debug(
                msg = f"DEBUG {self.cmd}",
            )
            p.shell(
                bg_start(self.session, f"{self.cmd}"),
                # chdir=str(self.remote_working_dir),
                task_name=f"Running {self.cmd} with the options",
            )
            results = p.results
        print(results)

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
        