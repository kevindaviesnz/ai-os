#include "../include/os_types.h"
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
#define SYS_UART_WRITE       6

extern void kpanic(const char *str);
extern void kernel_idle(void);
extern uint32_t loaded_module_count;
extern module_region_t module_regions[8];

typedef struct {
    uint32_t module_id;
    uint64_t sp_el0;
    uint64_t regs[31];
    uint64_t elr;
    uint8_t  initialized;
    uint8_t  in_handler;
    uint8_t  has_msg;
    os_message_t mailbox;
    uint64_t handler_ptr;
} module_context_t;

static module_context_t module_contexts[8];

int is_valid_el0_pointer(uint64_t ptr, uint64_t size) {
    if (size > 0 && ptr + size < ptr) return 0;
    module_region_t *reg = get_region_for_current_module();
    if (!reg) return 0;
    if (ptr >= reg->stack_base && (ptr + size) <= (reg->stack_base + reg->stack_size)) return 1;
    if (ptr >= reg->code_base && (ptr + size) <= (reg->code_base + reg->code_size)) return 1;
    return 0;
}

const uint8_t capability_matrix[MODULE_COUNT][MODULE_COUNT] = {
    /* KERNEL  UART  SHELL  FS  */
    {  1,      1,    1,     1  },  /* KERNEL */
    {  1,      0,    1,     0  },  /* UART   */
    {  0,      1,    0,     1  },  /* SHELL  */
    {  0,      0,    1,     0  },  /* FS     */
};

int ipc_send(uint32_t sender_id, const os_message_t *msg) {
    uint32_t target_id = msg->target_id;
    if (sender_id >= MODULE_COUNT || target_id >= MODULE_COUNT) return IPC_ERR_INVALID;
    if (!capability_matrix[sender_id][target_id]) return IPC_ERR_DENIED;

    if (module_contexts[target_id].in_handler || module_contexts[target_id].has_msg) return IPC_ERR_INVALID;

    module_contexts[target_id].mailbox.target_id = msg->target_id;
    module_contexts[target_id].mailbox.type = msg->type;
    module_contexts[target_id].mailbox.length = msg->length;

    for (int i = 0; i < IPC_PAYLOAD_MAX_SIZE; i++) {
        module_contexts[target_id].mailbox.payload[i] = msg->payload[i];
    }

    module_contexts[target_id].has_msg = 1;
    return 0;
}

void dispatch_pending_messages(void) {
    extern char _stack_top[0];
    for (int i = 0; i < 8; i++) {
        if (module_contexts[i].initialized && module_contexts[i].has_msg && !module_contexts[i].in_handler) {
            module_contexts[i].has_msg = 0;
            module_contexts[i].in_handler = 1;

            uint64_t elr = module_contexts[i].handler_ptr;

            uint64_t sp_el0 = module_contexts[i].sp_el0;
            sp_el0 -= sizeof(os_message_t);
            sp_el0 &= ~0xFULL;

            os_message_t *dest = (os_message_t *)sp_el0;
            dest->target_id = module_contexts[i].mailbox.target_id;
            dest->type = module_contexts[i].mailbox.type;
            dest->length = module_contexts[i].mailbox.length;

            for (int p = 0; p < IPC_PAYLOAD_MAX_SIZE; p++) {
                dest->payload[p] = module_contexts[i].mailbox.payload[p];
            }

            uint64_t arg = sp_el0;
            uint64_t stack_top = (uint64_t)_stack_top;

            __asm__ volatile(
                "mov sp, %3\n\t"
                "msr elr_el1, %0\n\t"
                "msr sp_el0, %1\n\t"
                "msr spsr_el1, xzr\n\t"
                "mov x0, %2\n\t"
                "mov x1, xzr\n\t" "mov x2, xzr\n\t" "mov x3, xzr\n\t"
                "mov x4, xzr\n\t" "mov x5, xzr\n\t" "mov x6, xzr\n\t"
                "mov x7, xzr\n\t" "mov x8, xzr\n\t" "mov x9, xzr\n\t"
                "mov x10, xzr\n\t" "mov x11, xzr\n\t" "mov x12, xzr\n\t"
                "mov x13, xzr\n\t" "mov x14, xzr\n\t" "mov x15, xzr\n\t"
                "mov x16, xzr\n\t" "mov x17, xzr\n\t" "mov x18, xzr\n\t"
                "mov x19, xzr\n\t" "mov x20, xzr\n\t" "mov x21, xzr\n\t"
                "mov x22, xzr\n\t" "mov x23, xzr\n\t" "mov x24, xzr\n\t"
                "mov x25, xzr\n\t" "mov x26, xzr\n\t" "mov x27, xzr\n\t"
                "mov x28, xzr\n\t" "mov x29, xzr\n\t" "mov x30, xzr\n\t"
                "eret\n\t"
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
        uint64_t syscall_num = regs[REG_X8];
        module_region_t *reg = get_region_for_current_module();
        if (!reg) { kpanic("FATAL: SVC from unknown region\n"); }

        uint32_t current_id = reg->module_id;
        if (current_id >= 8) { kpanic("FATAL: module_id out of bounds\n"); }

        switch (syscall_num) {
            case SYS_MODULE_REGISTER:
            {
                module_contexts[current_id].module_id = current_id;
                module_contexts[current_id].handler_ptr = regs[REG_X1];
                regs[REG_X0] = 0;
                break;
            }
            case SYS_INIT_DONE:
            {
                module_contexts[current_id].initialized = 1;
                module_contexts[current_id].sp_el0 = reg->stack_base + reg->stack_size;

                uint32_t current_index = 0;
                for (uint32_t i = 0; i < loaded_module_count; i++) {
                    if (module_regions[i].module_id == current_id) { current_index = i; break; }
                }

                uint32_t next_index = current_index + 1;
                if (next_index < loaded_module_count) {
                    regs[32] = module_regions[next_index].code_base;
                    regs[33] = 0;
                    regs[34] = module_regions[next_index].stack_base + module_regions[next_index].stack_size;
                } else {
                    regs[32] = (uint64_t)kernel_idle;
                    regs[33] = 0x05;
                }
                regs[REG_X0] = 0;
                break;
            }
            case SYS_HANDLER_DONE:
            {
                module_contexts[current_id].in_handler = 0;
                regs[32] = (uint64_t)kernel_idle;
                regs[33] = 0x05;
                regs[REG_X0] = 0;
                break;
            }
            case SYS_IPC_SEND:
            {
                os_message_t *msg = (os_message_t *)regs[REG_X1];
                if (!is_valid_el0_pointer((uint64_t)msg, sizeof(os_message_t))) {
                    regs[REG_X0] = 2; break;
                }
                regs[REG_X0] = ipc_send(current_id, msg);
                break;
            }
            case SYS_UART_WRITE:
            {
                const char *str = (const char *)regs[REG_X0];
                uint64_t len = regs[REG_X1];
                volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
                for (uint64_t i = 0; i < len && str[i]; i++) {
                    *uart = (uint32_t)str[i];
                }
                regs[REG_X0] = 0;
                break;
            }
            default: regs[REG_X0] = 2; break;
        }
    } else {
        volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
        const char *hex = "0123456789ABCDEF";
        *uart = '\n'; *uart = 'E'; *uart = 'S'; *uart = 'R'; *uart = ':'; *uart = ' ';
        for (int i = 15; i >= 0; i--) *uart = hex[(esr >> (i * 4)) & 0xF];
        *uart = ' '; *uart = 'E'; *uart = 'L'; *uart = 'R'; *uart = ':'; *uart = ' ';
        uint64_t elr;
        __asm__ volatile("mrs %0, elr_el1" : "=r"(elr));
        for (int i = 15; i >= 0; i--) *uart = hex[(elr >> (i * 4)) & 0xF];
        *uart = '\n';
        kpanic("FATAL: Unhandled CPU Exception Caught!\n");
    }
}