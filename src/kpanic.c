#include "../include/os_types.h"

void kpanic(const char *msg) {
    volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
    while (*msg) {
        *uart = (uint32_t)*msg++;
    }
    while (1) {
        __asm__ volatile("wfe");
    }
}
