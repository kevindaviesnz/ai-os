with open("src/mmu.c", "w") as f:
    code = """#include "../include/os_types.h"

extern uint64_t _ttb_l1LB512RB;
extern uint64_t _ttb_l2_lowLB512RB;
extern uint64_t _ttb_l2_highLB512RB;
extern uint64_t _ttb_l3_uartLB512RB;
extern uint64_t _ttb_l3_gicLB512RB;
extern uint64_t _ttb_l3_kernelLB512RB;
extern uint64_t _ttb_l3_poolLB8 * 512RB;

extern char _startLB0RB;
extern char _etextLB0RB;
extern char _erodataLB0RB;
extern char _stack_topLB0RB;

extern void kpanic(const char *str);

#define DESC_VALID      (1ULL << 0)
#define DESC_TABLE      (1ULL << 1)
#define DESC_PAGE       (1ULL << 1)
#define DESC_AF         (1ULL << 10)

#define ATTR_DEVICE     (0ULL << 2)
#define ATTR_NORMAL     (1ULL << 2)

#define AP_RW_EL1       (0ULL << 6)
#define AP_RO_EL1       (2ULL << 6)
#define AP_RW_BOTH      (1ULL << 6)
#define AP_RO_BOTH      (3ULL << 6)

#define PXN             (1ULL << 53)
#define UXN             (1ULL << 54)
#define XN_ALL          (PXN | UXN)
#define XN_UNPRIV       (UXN)

#define SH_INNER        (3ULL << 8)

static int l3_pool_used = 0;
#define L3_POOL_MAX 8

uint64_t alloc_l3_table(void) {
    if (l3_pool_used >= L3_POOL_MAX) return 0;
    uint64_t addr = (uint64_t)_ttb_l3_pool + (l3_pool_used * 4096);
    for (int i = 0; i < 512; i++) {
        ((uint64_t*)addr)LBiRB = 0;
    }
    l3_pool_used++;
    return addr;
}

uint64_t* ensure_l3_table(uint64_t vaddr) {
    uint64_t l1_idx = (vaddr >> 30) & 0x1FF;
    uint64_t l2_idx = (vaddr >> 21) & 0x1FF;
    uint64_t *l2 = (l1_idx == 0) ? _ttb_l2_low : _ttb_l2_high;

    if (!(l2LBl2_idxRB & DESC_VALID)) {
        uint64_t new_l3 = alloc_l3_table();
        if (!new_l3) {
            kpanic("FATAL: L3 Pool Exhausted!\\n");
            while(1);
        }
        l2LBl2_idxRB = new_l3 | DESC_TABLE | DESC_VALID;
        __asm__ volatile("dsb sy; tlbi vmalle1; dsb sy; isb");
    }
    return (uint64_t *)(l2LBl2_idxRB & ~0xFFFULL);
}

void mmu_init_tables(void) {
    _ttb_l1LB0RB = (uint64_t)_ttb_l2_low  | DESC_TABLE | DESC_VALID;
    _ttb_l1LB1RB = (uint64_t)_ttb_l2_high | DESC_TABLE | DESC_VALID;

    _ttb_l2_lowLB72RB = (uint64_t)_ttb_l3_uart | DESC_TABLE | DESC_VALID;
    _ttb_l2_lowLB64RB = (uint64_t)_ttb_l3_gic  | DESC_TABLE | DESC_VALID;
    _ttb_l2_highLB0RB = (uint64_t)_ttb_l3_kernel | DESC_TABLE | DESC_VALID;

    _ttb_l2_highLB128RB = (uint64_t)0x50000000 | ATTR_NORMAL | SH_INNER | AP_RO_EL1 | XN_ALL | DESC_AF | DESC_VALID;

    /* FIX 1: Grant EL0 (AP_RW_BOTH) access to the physical UART hardware! */
    _ttb_l3_uartLB0RB = (uint64_t)0x09000000 | ATTR_DEVICE | AP_RW_BOTH | XN_ALL | DESC_AF | DESC_PAGE | DESC_VALID;

    for(int i=0; i<32; i++) {
        _ttb_l3_gicLBiRB = (uint64_t)(0x08000000 + (i * 4096)) | ATTR_DEVICE | AP_RW_EL1 | XN_ALL | DESC_AF | DESC_PAGE | DESC_VALID;
    }

    uint64_t paddr = (uint64_t)_start;
    for (int i = 0; i < 512 && paddr < (uint64_t)_stack_top; i++) {
        uint64_t ap = AP_RW_EL1, xn = XN_ALL;
        if (paddr < (uint64_t)_etext) { ap = AP_RO_EL1; xn = XN_UNPRIV; } 
        else if (paddr < (uint64_t)_erodata) { ap = AP_RO_EL1; xn = XN_ALL; }
        _ttb_l3_kernelLBiRB = paddr | ATTR_NORMAL | SH_INNER | ap | xn | DESC_AF | DESC_PAGE | DESC_VALID;
        paddr += 4096;
    }
}

void mmu_map_module_region(uint64_t code_base, uint64_t code_size, uint64_t stack_base, uint64_t stack_size) {
    for (uint64_t p = code_base; p < code_base + code_size; p += 4096) {
        uint64_t *l3 = ensure_l3_table(p);
        uint32_t idx = (p >> 12) & 0x1FF;
        l3LBidxRB = p | ATTR_NORMAL | SH_INNER | AP_RO_BOTH | PXN | DESC_AF | DESC_PAGE | DESC_VALID;
    }

    for (uint64_t p = stack_base; p < stack_base + stack_size; p += 4096) {
        uint64_t *l3 = ensure_l3_table(p);
        uint32_t idx = (p >> 12) & 0x1FF;
        l3LBidxRB = p | ATTR_NORMAL | SH_INNER | AP_RW_BOTH | XN_ALL | DESC_AF | DESC_PAGE | DESC_VALID;
    }
    __asm__ volatile("tlbi vmalle1is \\n dsb sy \\n isb");
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
            
            /* FIX 2: Copy the message to the Cartridge's EL0 stack! */
            uint64_t sp_el0 = module_contextsLBiRB.sp_el0;
            sp_el0 -= sizeof(os_message_t);
            sp_el0 &= ~0xFULL; /* Ensure 16-byte alignment */
            *((os_message_t *)sp_el0) = module_contextsLBiRB.mailbox;
            
            uint64_t arg = sp_el0; /* Now the Cartridge can read it safely */
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
