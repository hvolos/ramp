#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

char* fill_memory(unsigned int seed, size_t size) {
	fprintf(stderr, "INFO: Filling memory ...\n");
	
	char* buf = (char*) malloc(size);
	assert(buf != NULL);
	srand(seed);
	for (size_t i=0; i < size; i++) {
		buf[i] = rand() % 128;
	}
	return buf;
}

void check_memory(unsigned int seed, size_t size, char* buf) {
	fprintf(stderr, "INFO: Checking memory ...\n");
	
	assert(buf != NULL);
	srand(seed);
	for (size_t i=0; i < size; i++) {
		if (buf[i] != (rand() % 128)) {
			fprintf(stderr, "ERROR: Not matching byte at %zu\n", i);
			abort();
		}
	}
}

int main(int argc, char **argv) {
	if (argc < 3) {
		fprintf(stderr, "usage: %s <seed> <size_mb>\n", argv[0]); 
		return -1;
	}
	
	
	unsigned int seed = atoi(argv[1]);
	size_t size = atoi(argv[2])*1024*1024;
	
	fprintf(stderr, "INFO: seed == %u\n", seed);
	fprintf(stderr, "INFO: size == %zu\n", size);
	
	char* buf = fill_memory(seed, size);
	check_memory(seed, size, buf);
	return 0;
}
