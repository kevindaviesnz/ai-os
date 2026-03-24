#include "../include/os_loader.h"

extern void kpanic(const char *str);
extern void mmu_map_module_region(uint64_t code_base, uint64_t code_size, uint64_t stack_base, uint64_t stack_size);
extern int cartridge_verify(const uint8_t *cartridge, uint32_t size, const uint8_t *pub_key);

module_region_t module_regions[8];
uint32_t loaded_module_count = 0;
static uint64_t bump_ptr = MODULE_ALLOC_BASE;

void *memcpy(void *dest, const void *src, uint64_t n) {
    uint8_t *d = dest;
    const uint8_t *s = src;
    while (n--) *d++ = *s++;
    return dest;
}

uint64_t module_alloc(uint64_t size) {
    size = (size + 4095) & ~4095; 
    if (bump_ptr + size > MODULE_ALLOC_LIMIT) return 0; 
    uint64_t addr = bump_ptr;
    bump_ptr += size;
    return addr;
}

module_region_t* get_region_for_current_module(void) {
    uint64_t elr;
    __asm__ volatile("mrs %0, elr_el1" : "=r"(elr));
    for (uint32_t i = 0; i < loaded_module_count; i++) {
        if (elr >= module_regions[i].code_base &&
            elr <  module_regions[i].code_base + module_regions[i].code_size) {
            return &module_regions[i];
        }
    }
    return (module_region_t*)0;
}

/* THE TRUE BARE-METAL FIX: Manual AArch64 Cache Maintenance! */
void sync_cache(uint64_t start, uint64_t size) {
    uint64_t end = start + size;
    /* Clean D-Cache to Point of Unification (PoU) */
    for (uint64_t p = start & ~0x3FULL; p < end; p += 64) {
        __asm__ volatile("dc cvau, %0" :: "r"(p));
    }
    __asm__ volatile("dsb ish");
    
    /* Invalidate I-Cache to Point of Unification (PoU) */
    for (uint64_t p = start & ~0x3FULL; p < end; p += 64) {
        __asm__ volatile("ic ivau, %0" :: "r"(p));
    }
    __asm__ volatile("dsb ish \n isb");
}

void loader_init(void) {
    bundle_header_t *bundle = (bundle_header_t *)BUNDLE_PHYS_ADDR;

    if (bundle->magic != MAGIC_ATKB) {
        kpanic("FATAL: Invalid Bundle Magic!\n");
        return;
    }

    for (uint32_t i = 0; i < bundle->cartridge_count && i < 8; i++) {
        uint32_t offset = bundle->index[i].offset;
        uint32_t size = bundle->index[i].size;
        cartridge_header_t *cart = (cartridge_header_t *)((uint8_t*)bundle + offset);

        if (cart->magic != MAGIC_ATKM || cartridge_verify((uint8_t*)cart, size, 0) < 0) continue;

        uint64_t code_base = module_alloc(cart->code_size);
        uint64_t stack_alloc = module_alloc(cart->stack_size + 4096);
        if (!code_base || !stack_alloc) continue;
        uint64_t stack_base = stack_alloc + 4096; 

        mmu_map_module_region(code_base, cart->code_size, stack_base, cart->stack_size);

        uint8_t *payload_src = (uint8_t*)cart + sizeof(cartridge_header_t);
        memcpy((void*)code_base, payload_src, cart->code_size);

        /* Flush the caches securely */
        sync_cache(code_base, cart->code_size);

        module_regions[loaded_module_count].module_id = cart->module_id;
        module_regions[loaded_module_count].code_base = code_base;
        module_regions[loaded_module_count].code_size = cart->code_size;
        module_regions[loaded_module_count].stack_base = stack_base;
        module_regions[loaded_module_count].stack_size = cart->stack_size;
        loaded_module_count++;
    }
}
