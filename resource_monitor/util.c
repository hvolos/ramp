#include <stdarg.h>
#include <time.h>

int current_verbose_level = 0;

void printv(int message_verbose_level, const char *format, ...) {
    if (current_verbose_level >= message_verbose_level) {
        va_list args;
        va_start(args, format);
        vprintf(format, args);
        va_end(args);
    }
}

// Function to calculate the difference between two timespec structures in microseconds
static long diff_in_us(struct timespec *start, struct timespec *end) {
    return (end->tv_sec - start->tv_sec) * 1000000 + (end->tv_nsec - start->tv_nsec) / 1000;
}

// Function to spin until the specified number of microseconds has elapsed
void spin_microseconds(long microseconds) {
    struct timespec start, current;
    
    // Get the starting time
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    do {
        // Get the current time
        clock_gettime(CLOCK_MONOTONIC, &current);
    } while (diff_in_us(&start, &current) < microseconds);
}
