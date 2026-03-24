#ifndef OS_LOADER_H
#define OS_LOADER_H

#include "os_types.h"

#define MAGIC_ATKB 0x41544B42 /* 'ATKB' */
#define MAGIC_ATKM 0x41544B4D /* 'ATKM' */

#define BUNDLE_PHYS_ADDR   0x50000000
#define MODULE_ALLOC_BASE  0x41000000
#define MODULE_ALLOC_LIMIT 0x4F000000

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint32_t version;
    uint32_t cartridge_count;
    uint32_t reserved;
    struct {
        uint32_t offset;
        uint32_t size;
    } index[8];
} bundle_header_t;

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint32_t version;
    uint32_t module_id;
    uint32_t code_size;
    uint32_t stack_size;
    uint32_t reserved;
    uint8_t  signature[64];
} cartridge_header_t;

typedef struct {
    uint32_t module_id;
    uint64_t code_base;
    uint64_t code_size;
    uint64_t stack_base;
    uint64_t stack_size;
} module_region_t;

void loader_init(void);
module_region_t* get_region_for_current_module(void);

#endif
