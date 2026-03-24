import os

# 1. Generate the fully patched UART driver
with open("modules/uart/uart_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

#define UART0_DR ((volatile uint32_t *)0x09000000)

void uart_handler(os_message_t *msg);

void _start(void) {
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, uart_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_UART), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
                     
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    
    while(1) { __asm__ volatile("wfi"); }
}

void uart_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_CHAR_OUT) {
        /* THE FIX: Loop through the entire payload length! */
        for (uint32_t i = 0; i < msg->length; i++) {
            *UART0_DR = msg->payloadLBiRB;
        }
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))


# 2. Generate the fully patched Kernel Syscall Dispatcher
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

const uint8_t capability_matrixLBMODULE_COUNTRBLBMODULE_COUNTRB = {
    /* KERNEL  UART  SHELL  FS  */
    {  1,      1,    1,     1  },  /* KERNEL */
    {  1,      0,    1,     0  },  /* UART   */
    {  0,      1,    0,     1  },  /* SHELL  */
    {  0,      0,    1,     0  },  /* FS     */
};

int ipc_send(uint32_t sender_id, const os_message_t *msg) {
    uint32_t target_id = msg->target_id;
    if (sender_id >= MODULE_COUNT || target_id >= MODULE_COUNT) return IPC_ERR_INVALID; 
    if (!capability_matrixLBsender_idRBLBtarget_idRB) return IPC_ERR_DENIED;
    
    if (module_contextsLBtarget_idRB.in_handler || module_contextsLBtarget_idRB.has_msg) return IPC_ERR_INVALID;
    
    module_contextsLBtarget_idRB.mailbox.target_id = msg->target_id;
    module_contextsLBtarget_idRB.mailbox.type = msg->type;
    module_contextsLBtarget_idRB.mailbox.length = msg->length;
    
    for(int i=0; i<IPC_PAYLOAD_MAX_SIZE; i++) {
        module_contextsLBtarget_idRB.mailbox.payloadLBiRB = msg->payloadLBiRB;
    }
    
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
            
            os_message_t *dest = (os_message_t *)sp_el0;
            dest->target_id = module_contextsLBiRB.mailbox.target_id;
            dest->type = module_contextsLBiRB.mailbox.type;
            dest->length = module_contextsLBiRB.mailbox.length;
            
            /* THE KERNEL FIX: Copy all 16 payload bytes to User Space, not just 4! */
            for(int p=0; p<IPC_PAYLOAD_MAX_SIZE; p++) {
                dest->payloadLBpRB = module_contextsLBiRB.mailbox.payloadLBpRB;
            }
            
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

                uint32_t current_index = 0;
                for(uint32_t i=0; i<loaded_module_count; i++) {
                    if (module_regionsLBiRB.module_id == current_id) { current_index = i; break; }
                }

                uint32_t next_index = current_index + 1;
                if (next_index < loaded_module_count) {
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
        volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
        const char *hex = "0123456789ABCDEF";
        *uart = '\\n'; *uart = 'E'; *uart = 'S'; *uart = 'R'; *uart = ':'; *uart = ' ';
        for (int i = 15; i >= 0; i--) *uart = hexLB(esr >> (i * 4)) & 0xFRB;
        *uart = ' '; *uart = 'E'; *uart = 'L'; *uart = 'R'; *uart = ':'; *uart = ' ';
        uint64_t elr;
        __asm__ volatile("mrs %0, elr_el1" : "=r"(elr));
        for (int i = 15; i >= 0; i--) *uart = hexLB(elr >> (i * 4)) & 0xFRB;
        *uart = '\\n';
        kpanic("FATAL: Unhandled CPU Exception Caught!\\n");
    }
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))