#include "../include/os_types.h"
#include "../include/os_dispatcher.h"

#define GICD_BASE 0x08000000
#define GICC_BASE 0x08010000
#define UART_IRQ  33
#define TIMER_IRQ 30

extern volatile uint64_t system_ticks;
extern uint64_t timer_tick_interval;

void gic_init(void) {
    *(volatile uint32_t*)(GICD_BASE + 0x000) = 1;

    /* Enable UART (SPI 33 -> ISENABLER bit 1) */
    *(volatile uint32_t*)(GICD_BASE + 0x104) = (1 << 1);
    
    /* Enable Timer (PPI 30 -> ISENABLER bit 30) (WARNING-05) */
    *(volatile uint32_t*)(GICD_BASE + 0x100) = (1 << 30);

    /* Priority: Timer = 0x80 (Higher), UART = 0xA0 (Lower) */
    volatile uint8_t* gicd_ipriorityr = (uint8_t*)(GICD_BASE + 0x400);
    *(gicd_ipriorityr + TIMER_IRQ) = 0x80;
    *(gicd_ipriorityr + UART_IRQ)  = 0xA0;

    volatile uint8_t* gicd_itargetsr = (uint8_t*)(GICD_BASE + 0x800);
    *(gicd_itargetsr + UART_IRQ) = 1;

    *(volatile uint32_t*)(GICC_BASE + 0x004) = 0xF0;
    *(volatile uint32_t*)(GICC_BASE + 0x000) = 1;
}

void gic_irq_handler(void) {
    uint32_t iar = *(volatile uint32_t*)(GICC_BASE + 0x00C);
    uint32_t irq = iar & 0x3FF;

    if (irq == 1023) return;

    if (irq == TIMER_IRQ) {
        /* RELOAD MUST HAPPEN BEFORE EOIR (ADVISORY-09) */
        __asm__ volatile("msr cntp_tval_el0, %0" :: "r"(timer_tick_interval));
        system_ticks++;
        
        /* Send a tick message to the Shell every 100 ticks (1 second) */
        if (system_ticks % 100 == 0) {
            os_message_t msg = {0};
            msg.target_id = SYS_MOD_SHELL;
            msg.type = IPC_TYPE_SYS_ACK; /* Repurposed as Tick event for now */
            msg.length = 0;
            ipc_send(SYS_MOD_KERNEL, &msg);
        }
    }
    else if (irq == UART_IRQ) {
        uint8_t c = *(volatile uint32_t*)(0x09000000);
        os_message_t msg = {0};
        msg.target_id = SYS_MOD_SHELL;
        msg.type = IPC_TYPE_CHAR_IN;
        msg.length = 1;
        *msg.payload = c;
        ipc_send(SYS_MOD_UART, &msg);
    }

    *(volatile uint32_t*)(GICC_BASE + 0x010) = iar;
}
