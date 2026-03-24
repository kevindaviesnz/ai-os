with open("src/kernel.c", "w") as f:
    code = """#include "../include/os_types.h"
#include "../include/os_loader.h"
#include "../include/os_dispatcher.h" /* THE MISSING HEADER! */

extern void mmu_init_tables(void);
extern void gic_init(void);
extern void timer_init(void);
extern void dispatcher_init(void);
extern void kpanic(const char *msg);
extern void launch_cartridge(uint64_t elr, uint64_t sp_el0);
extern void dispatch_pending_messages(void);
extern int ipc_send(uint32_t sender_id, os_message_t *msg);

extern uint32_t loaded_module_count;
extern module_region_t module_regionsLB8RB;
extern uint32_t system_ticks;

#define SYS_MOD_SHELL 2

void irq_handler(uint64_t *regs) {
    (void)regs;
    volatile uint32_t *gicc = (volatile uint32_t *)0x08010000;
    uint32_t iar = giccLB3RB;
    uint32_t irq = iar & 0x3FF;

    if (irq == 30) { 
        system_ticks++;
        uint64_t cntpct;
        __asm__ volatile("mrs %0, cntpct_el0" : "=r"(cntpct));
        __asm__ volatile("msr cntp_tval_el0, %0" :: "r"(625000)); 
        
        if (system_ticks % 100 == 0) {
            os_message_t msg;
            msg.target_id = SYS_MOD_SHELL;
            msg.type = IPC_TYPE_SYS_ACK; 
            msg.length = 0;
            ipc_send(0, &msg); 
        }
    } else if (irq == 33) { 
        volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
        uint8_t c = (uint8_t)(*uart);
        
        os_message_t msg;
        msg.target_id = SYS_MOD_SHELL;
        msg.type = IPC_TYPE_CHAR_IN;
        msg.length = 1;
        msg.payloadLB0RB = c;
        ipc_send(0, &msg); 
    }

    giccLB4RB = iar; 
}

void kernel_idle(void) {
    while (1) {
        dispatch_pending_messages();
        __asm__ volatile("wfi");
    }
}

void kernel_main(void) {
    mmu_init_tables();
    __asm__ volatile("msr sctlr_el1, %0" :: "r"(1 | (1 << 2) | (1 << 12))); 

    gic_init();
    timer_init();
    dispatcher_init();
    loader_init(); 

    if (loaded_module_count > 0) {
        launch_cartridge(module_regionsLB0RB.code_base, 
                         module_regionsLB0RB.stack_base + module_regionsLB0RB.stack_size);
    } else {
        kpanic("FATAL: No cartridges loaded.\\n");
    }
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))
