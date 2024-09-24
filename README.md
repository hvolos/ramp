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

## Configuring fault injection


Setting fault rate

```
echo 1000 | sudo tee /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_distr
sudo cat /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_distr
```

Enabling fault injection

```
echo 1 | sudo tee /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_enable
```
