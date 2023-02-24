all: random

random: random.c
	gcc -std=c99 -Wall random.c -o random
	
image: random
	docker build -t random:latest .
