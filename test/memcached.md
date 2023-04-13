## memcache-perf

git clone git@github.com:hvolos/memcache-perf.git
cd memcache-perf
git checkout -b zmq-4.0.4 origin/zmq-4.0.4

make

## memcached

docker kill my-memcache; docker rm my-memcache

docker run --name my-memcache -m 64m -d memcached memcached -m 512

/users/hvolos01/memcache-perf/mcperf -s 172.17.0.2 -r 300000
