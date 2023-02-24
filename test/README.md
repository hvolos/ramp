docker run random 1 2
docker run -m 64m random 1 2

You can ignore the message:
WARNING: Your kernel does not support swap limit capabilities or the cgroup is not mounted. Memory limited without swap.

Explanation:
Docker daemon relies on the following virtual files to implement memory and swap limits:

/sys/fs/cgroup/memory/memory.limit_in_bytes
/sys/fs/cgroup/memory/memory.memsw.limit_in_bytes

memory.memsw.limit_in_bytes
Specifies the maximum usage permitted for user memory plus swap space. The default units are bytes, but you can also specify a k or K, m or M, and g or G suffix for kilobytes, megabytes, and gigabytes respectively. A value of -1 removes the limit.

memory.memsw.max_usage_in_bytes
Reports the maximum amount of user memory and swap space in bytes used by tasks in the cgroup.


Monitor swap use:
 
while true; do sudo swapon -s; sleep 1; done
