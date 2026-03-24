#include "../include/os_types.h"

volatile uint64_t system_ticks = 0;
uint64_t timer_tick_interval = 0;

void timer_init(void) {
    uint64_t freq;
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(freq));

    if (freq == 0) {
        /* Fallback for QEMU if firmware didn't set it (WARNING-04) */
        freq = 62500000ULL; 
    }

    /* 10ms tick interval */
    timer_tick_interval = freq / 100;
    
    __asm__ volatile("msr cntp_tval_el0, %0" :: "r"(timer_tick_interval));
    __asm__ volatile("msr cntp_ctl_el0, %0" :: "r"((uint64_t)1));
}
