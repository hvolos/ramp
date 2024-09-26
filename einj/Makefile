# Makefile for einj module
obj-m += einj.o

KVERSION = 4.4.0  # Replace this with your kernel version
KDIR = /usr/src/linux-headers-$(KVERSION)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
