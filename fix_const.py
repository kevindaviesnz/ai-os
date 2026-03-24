with open("src/kernel.c", "w") as f:
    code = """#include "../include/os_types.h"
#include "../include/os_loader.h"
#include "../include/os_dispatcher.h"

extern void mmu_init_tables(void);
extern void gic_init(void);
extern void timer_init(void);
extern void dispatcher_init(void);
extern void kpanic(const char *msg);
extern void launch_cartridge(uint64_t elr, uint64_t sp_el0);
extern void dispatch_pending_messages(void);

/* Removed the conflicting manual extern declaration of ipc_send! */

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

with open("src/syscall.c", "w") as f:
    code = """#include "../include/os_types.h"
#include "../include/os_dispatcher.h"
#include "../include/os_loader.h"

#define REG_X0  0
#define REG_X1  1
#define REG_X8  8 

#define SYS_IPC_SEND         1
#define SYS_IPC_RECEIVE      2
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

extern void kpanic(const char *str);
extern void kernel_idle(void);
extern uint32_t loaded_module_count;
extern module_region_t module_regionsLB8RB;

typedef struct {
    uint32_t module_id;
    uint64_t sp_el0;
    uint64_t regsLB31RB;
    uint64_t elr;
    uint8_t  initialized;
    uint8_t  in_handler;
    uint8_t  has_msg;
    os_message_t mailbox;
    uint64_t handler_ptr;
} module_context_t;

static module_context_t module_contextsLB8RB;

int is_valid_el0_pointer(uint64_t ptr, uint64_t size) {
    if (size > 0 && ptr + size < ptr) return 0;
    module_region_t *reg = get_region_for_current_module();
    if (!reg) return 0;
    if (ptr >= reg->stack_base && (ptr + size) <= (reg->stack_base + reg->stack_size)) return 1;
    if (ptr >= reg->code_base && (ptr + size) <= (reg->code_base + reg->code_size)) return 1;
    return 0; 
}

/* Added 'const' to exactly match the header definition */
int ipc_send(uint32_t sender_id, const os_message_t *msg) {
    (void)sender_id;
    uint32_t target_id = msg->target_id;
    if (target_id >= 8) return 2; 
    if (module_contextsLBtarget_idRB.in_handler || module_contextsLBtarget_idRB.has_msg) return 2;
    
    module_contextsLBtarget_idRB.mailbox = *msg;
    module_contextsLBtarget_idRB.has_msg = 1;
    return 0; 
}

void dispatch_pending_messages(void) {
    extern char _stack_topLB0RB;
    for (int i = 0; i < 8; i++) {
        if (module_contextsLBiRB.initialized && module_contextsLBiRB.has_msg && !module_contextsLBiRB.in_handler) {
            module_contextsLBiRB.has_msg = 0;
            module_contextsLBiRB.in_handler = 1;
            
            uint64_t elr = module_contextsLBiRB.handler_ptr;
            uint64_t sp_el0 = module_contextsLBiRB.sp_el0;
            uint64_t arg = (uint64_t)&module_contextsLBiRB.mailbox;
            uint64_t stack_top = (uint64_t)_stack_top;

            __asm__ volatile(
                "mov sp, %3\\n\\t"
                "msr elr_el1, %0\\n\\t"
                "msr sp_el0, %1\\n\\t"
                "msr spsr_el1, xzr\\n\\t"
                "mov x0, %2\\n\\t"
                "mov x1, xzr\\n\\t" "mov x2, xzr\\n\\t" "mov x3, xzr\\n\\t"
                "mov x4, xzr\\n\\t" "mov x5, xzr\\n\\t" "mov x6, xzr\\n\\t"
                "mov x7, xzr\\n\\t" "mov x8, xzr\\n\\t" "mov x9, xzr\\n\\t"
                "mov x10, xzr\\n\\t" "mov x11, xzr\\n\\t" "mov x12, xzr\\n\\t"
                "mov x13, xzr\\n\\t" "mov x14, xzr\\n\\t" "mov x15, xzr\\n\\t"
                "mov x16, xzr\\n\\t" "mov x17, xzr\\n\\t" "mov x18, xzr\\n\\t"
                "mov x19, xzr\\n\\t" "mov x20, xzr\\n\\t" "mov x21, xzr\\n\\t"
                "mov x22, xzr\\n\\t" "mov x23, xzr\\n\\t" "mov x24, xzr\\n\\t"
                "mov x25, xzr\\n\\t" "mov x26, xzr\\n\\t" "mov x27, xzr\\n\\t"
                "mov x28, xzr\\n\\t" "mov x29, xzr\\n\\t" "mov x30, xzr\\n\\t"
                "eret\\n\\t"
                :: "r"(elr), "r"(sp_el0), "r"(arg), "r"(stack_top)
            );
            __builtin_unreachable();
        }
    }
}

void syscall_handler(uint64_t *regs) {
    uint64_t esr;
    __asm__ volatile("mrs %0, esr_el1" : "=r"(esr));
    uint32_t ec = (esr >> 26) & 0x3F;

    if (ec == 0x15) { 
        uint64_t syscall_num = regsLBREG_X8RB;
        module_region_t *reg = get_region_for_current_module();
        if (!reg) { kpanic("FATAL: SVC from unknown region\\n"); }
        
        uint32_t current_id = reg->module_id;
        if (current_id >= 8) { kpanic("FATAL: module_id out of bounds\\n"); }

        switch (syscall_num) {
            case SYS_MODULE_REGISTER:
            {
                module_contextsLBcurrent_idRB.module_id = current_id;
                module_contextsLBcurrent_idRB.handler_ptr = regsLBREG_X1RB;
                regsLBREG_X0RB = 0;
                break;
            }
            case SYS_INIT_DONE:
            {
                module_contextsLBcurrent_idRB.initialized = 1;
                module_contextsLBcurrent_idRB.sp_el0 = reg->stack_base + reg->stack_size;

                uint32_t next_id = current_id + 1;
                if (next_id < loaded_module_count) {
                    regsLB31RB = module_regionsLBnext_idRB.code_base; 
                    regsLB33RB = module_regionsLBnext_idRB.stack_base + module_regionsLBnext_idRB.stack_size; 
                } else {
                    regsLB31RB = (uint64_t)kernel_idle;
                    regsLB32RB = 0x05; 
                }
                regsLBREG_X0RB = 0; 
                break;
            }
            case SYS_HANDLER_DONE:
            {
                module_contextsLBcurrent_idRB.in_handler = 0;
                regsLB31RB = (uint64_t)kernel_idle;
                regsLB32RB = 0x05;
                regsLBREG_X0RB = 0;
                break;
            }
            case SYS_IPC_SEND:
            {
                os_message_t *msg = (os_message_t*)regsLBREG_X1RB;
                if (!is_valid_el0_pointer((uint64_t)msg, sizeof(os_message_t))) {
                    regsLBREG_X0RB = 2; break;
                }
                regsLBREG_X0RB = ipc_send(current_id, msg);
                break;
            }
            default: regsLBREG_X0RB = 2; break;
        }
    } else {
        kpanic("FATAL: Hardware Sync Exception (Not SVC)\\n");
    }
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))
