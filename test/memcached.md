## memcache-perf

git clone git@github.com:hvolos/memcache-perf.git
cd memcache-perf
git checkout -b zmq-4.0.4 origin/zmq-4.0.4

sudo apt-get -y install libevent-dev libzmq3-dev
sudo apt-get -y build-dep memcached

make

## memcached

docker kill my-memcache; docker rm my-memcache

docker run --name my-memcache -m 64m -d memcached memcached -m 512

/users/hvolos01/memcache-perf/mcperf -s 172.17.0.2 -r 300000

loadonly

/users/hvolos01/memcache-perf/mcperf -s 172.17.0.2 -r 300000 --loadonly

high concurrency

/users/hvolos01/memcache-perf/mcperf -s 172.17.0.2 -r 300000 -T 24 c 8 --noload

larger working set

docker run --name my-memcache -m 1g -d memcached memcached -m 2097152
