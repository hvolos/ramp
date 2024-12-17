Replication-Aware Memory-error Protection (RAMP) offers a framework for designing and analyzing two-tier memory resilience schemes, where an upper memory-replication tier is used to handle errors that a lower memory-protection tier cannot tolerate. RAMP provides analytical models that enable system designers and operators to understand the interaction between the two protection tiers and assess how
the lower tier’s protection strength affects the overall protection provided by multiple replicas in the upper tier. 

## Resilience Evaluation

Use model/ to reason about resilience of two-tier protection scheme. 

## Performance Evaluation

Configure CloudLab r320 machines, with Linux kernel 4.4 and Mellanox OFED 4.1.

Use test.py to deploy Hydra, Memcached, and conduct synthetic fault injection experiments

### Verifying Memcached session 

Verify Memcached is running on the manager node

List all sessions:
tmux ls

Attach to session
tmux at -t mysession

Detach from session
CTRL+B then D

### Verifying memory cgroup

Verify memctl memory limit

cat /sys/fs/cgroup/memory/memctl/memory.limit_in_bytes

Verify memcached running under memctl cgroup

cat /proc/$(ps aux | grep memcached | grep users | awk '{print $2}')/cgroup

### Checking swap usage

swapon -s

### Configuring fault injection

Setting fault rate

```
echo 1000 | sudo tee /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_distr
sudo cat /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_distr
```

Enabling fault injection

```
echo 1 | sudo tee /sys/kernel/config/hydra/hydrahost0/hydra0/fault_injection_enable
```
