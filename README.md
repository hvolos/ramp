## Verifying Memcached session 

Verify Memcached is running on the manager node

List all sessions:
tmux ls

Attach to session
tmux at -t mysession

Detach from session
CTRL+B then D

## Verifying memory cgroup

Verify memctl memory limit

cat /sys/fs/cgroup/memory/memctl/memory.limit_in_bytes

Verify memcached running under memctl cgroup

cat /proc/$(ps aux | grep memcached | grep users | awk '{print $2}')/cgroup

## Checking swap usage

swapon -s