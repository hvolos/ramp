#ifndef UTIL_H
#define UTIL_H

#define PV_NOTICE 5
#define PV_INFO 6

// Function to print messages depending on verbosity level
void printv(int message_verbose_level, const char *format, ...);

// Function to spin until the specified number of microseconds has elapsed
void spin_microseconds(long microseconds);

#endif // UTIL_H
