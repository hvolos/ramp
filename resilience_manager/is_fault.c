#include "infiniswap.h"
#include "mt19937-64.h"

void IS_fault_injection_init(struct IS_fault_injection *IS_fault_injection)
{
    int i;

	IS_fault_injection->inject_fault = 0;
	IS_fault_injection->fault_rate = 1000000000ULL;
    for (i=0; i<NDISKS; i++){
    	IS_fault_injection->disk_fault[i].access_count = 0;
        IS_fault_injection->disk_fault[i].access_count_before_next_fault = IS_fault_injection->fault_rate;
    }
}

void IS_fault_injection_enable(struct IS_fault_injection *IS_fault_injection, unsigned int enable)
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

void IS_fault_injection_distr(struct IS_fault_injection *IS_fault_injection, const char* distr)
{
    unsigned long long fault_rate;
    sscanf(distr, "%lld", &fault_rate);

    init_uniform_distr(IS_fault_injection, fault_rate);
}

void IS_fault_injection_access(struct IS_fault_injection *IS_fault_injection, unsigned int disk)
{
    IS_fault_injection->disk_fault[disk].access_count++;
    IS_fault_injection->disk_fault[disk].access_count_before_next_fault--;
}

int IS_fault_injection_inject_fault(struct IS_fault_injection *IS_fault_injection, unsigned int disk)
{
    if (IS_fault_injection->inject_fault == 1 && 
        IS_fault_injection->disk_fault[disk].access_count_before_next_fault == 0)
    {
        IS_fault_injection->disk_fault[disk].access_count_before_next_fault = 
            1 + genrand64_uint64(&IS_fault_injection->disk_fault[disk].seed) % (2*IS_fault_injection->fault_rate);
        return 1;
    }

    return 0;
}