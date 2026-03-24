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
                uint32_t claimed_id = regsLBREG_X0RB;
                uint64_t handler_ptr = regsLBREG_X1RB;
                if (claimed_id != current_id) { regsLBREG_X0RB = IPC_ERR_DENIED; break; }
                if (handler_ptr < reg->code_base || handler_ptr >= (reg->code_base + reg->code_size)) {
                    regsLBREG_X0RB = IPC_ERR_INVALID; break;
                }
                module_contextsLBcurrent_idRB.module_id = current_id;
                module_contextsLBcurrent_idRB.handler_ptr = handler_ptr;
                regsLBREG_X0RB = 0;
                break;
            }
            case SYS_INIT_DONE:
            {
                module_contextsLBcurrent_idRB.initialized = 1;
                module_contextsLBcurrent_idRB.sp_el0 = reg->stack_base + reg->stack_size;
                for(int i=0; i<31; i++) module_contextsLBcurrent_idRB.regsLBiRB = regsLBiRB;

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
                if (!module_contextsLBcurrent_idRB.in_handler) {
                    regsLBREG_X0RB = IPC_ERR_INVALID; break;
                }
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
                    regsLBREG_X0RB = IPC_ERR_INVALID; break;
                }
                regsLBREG_X0RB = ipc_send(current_id, msg);
                break;
            }
            default: regsLBREG_X0RB = IPC_ERR_DENIED; break;
        }
    } else {
        kpanic("FATAL: Unhandled EL0 Sync Exception\\n");
    }
}
"""
    code = code.replace("LB", chr(91)).replace("RB", chr(93))
    f.write(code)
