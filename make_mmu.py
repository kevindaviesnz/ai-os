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

    /* THE FIX: Map the ATKB Bundle at 0x50000000 as a 2MB Block */
    /* Index 128 in l2_high corresponds exactly to 0x50000000 */
    _ttb_l2_highLB128RB = (uint64_t)0x50000000 | ATTR_NORMAL | SH_INNER | AP_RO_EL1 | XN_ALL | DESC_AF | DESC_VALID;

    _ttb_l3_uartLB0RB = (uint64_t)0x09000000 | ATTR_DEVICE | AP_RW_EL1 | XN_ALL | DESC_AF | DESC_PAGE | DESC_VALID;

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
