#include "infiniswap.h"
#include "mt19937-64.h"

static void init_uniform_distr(struct IS_fault_injection *IS_fault_injection, unsigned long long fault_rate) 
{
    int i;
	IS_fault_injection->fault_rate = fault_rate;
    for (i=0; i<NDISKS; i++){
    	init_genrand64(&IS_fault_injection->disk_fault[i].seed, 1);
    	IS_fault_injection->disk_fault[i].access_count = 0;
        IS_fault_injection->disk_fault[i].access_count_before_next_fault = 
            genrand64_uint64(&IS_fault_injection->disk_fault[i].seed) % (2*fault_rate);
    }
}

void IS_fault_injection_init(struct IS_fault_injection *IS_fault_injection)
{
	IS_fault_injection->inject_fault = 0;

    init_uniform_distr(IS_fault_injection, 1000000000ULL);
}

unsigned int IS_fault_injection_enable(struct IS_fault_injection *IS_fault_injection)
{
	return IS_fault_injection->inject_fault;
}

void IS_fault_injection_set_enable(struct IS_fault_injection *IS_fault_injection, unsigned int enable)
{
	IS_fault_injection->inject_fault = enable;
}

unsigned long long IS_fault_injection_fault_count(struct IS_fault_injection *IS_fault_injection)
{
	int i;
    unsigned long long count = 0;
    for (i=0; i<NDISKS; i++){
        count += IS_fault_injection->disk_fault[i].fault_count;
    }
    return count;
}

void IS_fault_injection_set_distr(struct IS_fault_injection *IS_fault_injection, const char* distr)
{
    unsigned long long fault_rate;
    sscanf(distr, "%llu", &fault_rate);

    init_uniform_distr(IS_fault_injection, fault_rate);
}

ssize_t IS_fault_injection_distr(struct IS_fault_injection *IS_fault_injection, char* distr)
{
    return snprintf(distr, PAGE_SIZE, "%d\n", IS_fault_injection->fault_rate);
}

void IS_fault_injection_access(struct IS_fault_injection *IS_fault_injection, unsigned int disk)
{
    // Benign race condition: 
    // The counter update is subject to a race condition, but this is acceptable because 
    // we only need an approximate value.
    IS_fault_injection->disk_fault[disk].access_count++;
    IS_fault_injection->disk_fault[disk].access_count_before_next_fault--;
}

int IS_fault_injection_inject_fault(struct IS_fault_injection *IS_fault_injection, unsigned int disk)
{
    if (IS_fault_injection->inject_fault == 1 && 
        IS_fault_injection->disk_fault[disk].access_count_before_next_fault <= 0)
    {
        IS_fault_injection->disk_fault[disk].fault_count++;
        IS_fault_injection->disk_fault[disk].access_count_before_next_fault = 
            1 + genrand64_uint64(&IS_fault_injection->disk_fault[disk].seed) % (2*IS_fault_injection->fault_rate);
        return 1;
    }

    return 0;
}
