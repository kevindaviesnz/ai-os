with open("src/vectors.S", "w") as f:
    code = """.macro kernel_entry
    sub sp, sp, #288
    stp x0, x1, [sp, #16 * 0]
    stp x2, x3, [sp, #16 * 1]
    stp x4, x5, [sp, #16 * 2]
    stp x6, x7, [sp, #16 * 3]
    stp x8, x9, [sp, #16 * 4]
    stp x10, x11, [sp, #16 * 5]
    stp x12, x13, [sp, #16 * 6]
    stp x14, x15, [sp, #16 * 7]
    stp x16, x17, [sp, #16 * 8]
    stp x18, x19, [sp, #16 * 9]
    stp x20, x21, [sp, #16 * 10]
    stp x22, x23, [sp, #16 * 11]
    stp x24, x25, [sp, #16 * 12]
    stp x26, x27, [sp, #16 * 13]
    stp x28, x29, [sp, #16 * 14]
    str x30, [sp, #16 * 15]
    
    mrs x21, elr_el1
    mrs x22, spsr_el1
    stp x21, x22, [sp, #16 * 16]
    
    mrs x21, sp_el0
    str x21, [sp, #16 * 17]
.endm

.macro kernel_exit
    ldr x21, [sp, #16 * 17]
    msr sp_el0, x21
    
    ldp x21, x22, [sp, #16 * 16]
    msr elr_el1, x21
    msr spsr_el1, x22
    
    ldp x28, x29, [sp, #16 * 14]
    ldr x30, [sp, #16 * 15]
    ldp x26, x27, [sp, #16 * 13]
    ldp x24, x25, [sp, #16 * 12]
    ldp x22, x23, [sp, #16 * 11]
    ldp x20, x21, [sp, #16 * 10]
    ldp x18, x19, [sp, #16 * 9]
    ldp x16, x17, [sp, #16 * 8]
    ldp x14, x15, [sp, #16 * 7]
    ldp x12, x13, [sp, #16 * 6]
    ldp x10, x11, [sp, #16 * 5]
    ldp x8, x9, [sp, #16 * 4]
    ldp x6, x7, [sp, #16 * 3]
    ldp x4, x5, [sp, #16 * 2]
    ldp x2, x3, [sp, #16 * 1]
    ldp x0, x1, [sp, #16 * 0]
    add sp, sp, #288
    eret
.endm

.align 11
.global vectors
vectors:
    .align 7; b default_handler 
    .align 7; b default_handler 
    .align 7; b default_handler 
    .align 7; b default_handler 

    .align 7; b kernel_sync     
    .align 7; b kernel_irq      /* FIX 3: Catch Timer Interrupts during Kernel Idle! */
    .align 7; b default_handler 
    .align 7; b default_handler 

    .align 7; b el0_sync        
    .align 7; b el0_irq         
    .align 7; b default_handler 
    .align 7; b default_handler 

    .align 7; b default_handler 
    .align 7; b default_handler 
    .align 7; b default_handler 
    .align 7; b default_handler 

kernel_sync:
    kernel_entry
    mov x0, sp
    bl syscall_handler
    kernel_exit

kernel_irq:
    kernel_entry
    mov x0, sp
    bl irq_handler
    kernel_exit

el0_sync:
    kernel_entry
    mov x0, sp
    bl syscall_handler
    kernel_exit

el0_irq:
    kernel_entry
    mov x0, sp
    bl irq_handler
    kernel_exit

default_handler:
    b default_handler
"""
    f.write(code)

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
            sp_el0 -= sizeof(os_message_t);
            sp_el0 &= ~0xFULL; 
            *((os_message_t *)sp_el0) = module_contextsLBiRB.mailbox;
            
            uint64_t arg = sp_el0; 
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

                /* FIX 2: Look up the next cartridge by array index! */
                uint32_t current_index = 0;
                for(uint32_t i=0; i<loaded_module_count; i++) {
                    if (module_regionsLBiRB.module_id == current_id) { current_index = i; break; }
                }

                uint32_t next_index = current_index + 1;
                if (next_index < loaded_module_count) {
                    /* FIX 1: The true indices of the Exception Frame! */
                    regsLB32RB = module_regionsLBnext_indexRB.code_base; 
                    regsLB33RB = 0; 
                    regsLB34RB = module_regionsLBnext_indexRB.stack_base + module_regionsLBnext_indexRB.stack_size; 
                } else {
                    regsLB32RB = (uint64_t)kernel_idle;
                    regsLB33RB = 0x05; 
                }
                regsLBREG_X0RB = 0; 
                break;
            }
            case SYS_HANDLER_DONE:
            {
                module_contextsLBcurrent_idRB.in_handler = 0;
                regsLB32RB = (uint64_t)kernel_idle;
                regsLB33RB = 0x05;
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
