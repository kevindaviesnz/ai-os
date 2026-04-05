#include "../include/os_types.h"
#include "../include/os_loader.h"
#include "../include/os_dispatcher.h"

extern void mmu_init_tables(void);
extern void gic_init(void);
extern void timer_init(void);
extern void dispatcher_init(void);
extern void kpanic(const char *msg);
extern void dispatch_pending_messages(void);

extern uint32_t loaded_module_count;
extern module_region_t module_regions[8];
extern uint32_t system_ticks;

#define INPUT_QUEUE_SIZE 32
static volatile uint8_t input_queue[INPUT_QUEUE_SIZE];
static volatile uint32_t input_head = 0;
static volatile uint32_t input_tail = 0;

void irq_handler(uint64_t *regs) {
    (void)regs;
    volatile uint32_t *gicc = (volatile uint32_t *)0x08010000;
    uint32_t iar = gicc[3];
    uint32_t irq = iar & 0x3FF;

    if (irq == 30) {
        system_ticks++;
        __asm__ volatile("msr cntp_tval_el0, %0" :: "r"(625000));
    } else if (irq == 33) {
        volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
        uint8_t c = (uint8_t)(*uart);
        uint32_t next = (input_tail + 1) % INPUT_QUEUE_SIZE;
        if (next != input_head) {
            input_queue[input_tail] = c;
            input_tail = next;
        }
    }

    gicc[4] = iar;
}

static void drain_input_queue(void) {
    while (input_head != input_tail) {
        os_message_t msg;
        msg.target_id = SYS_MOD_SHELL;
        msg.type = IPC_TYPE_CHAR_IN;
        msg.length = 1;
        msg.payload[0] = input_queue[input_head];
        if (ipc_send(0, &msg) != 0) break;
        input_head = (input_head + 1) % INPUT_QUEUE_SIZE;
    }
}

void kernel_idle(void) {
    while (1) {
        drain_input_queue();
        dispatch_pending_messages();
        __asm__ volatile("wfi");
    }
}

void boot_first_cartridge(uint64_t elr, uint64_t sp_el0) {
    __asm__ volatile(
        "msr elr_el1, %0\n\t"
        "msr sp_el0, %1\n\t"
        "msr spsr_el1, xzr\n\t"
        "eret\n\t"
        :: "r"(elr), "r"(sp_el0)
    );
    __builtin_unreachable();
}

void kernel_main(void) {
    mmu_init_tables();
    __asm__ volatile("msr sctlr_el1, %0" :: "r"(1 | (1 << 2) | (1 << 12)));

    gic_init();
    timer_init();
    dispatcher_init();
    loader_init();

    if (loaded_module_count > 0) {
        boot_first_cartridge(module_regions[0].code_base,
                             module_regions[0].stack_base + module_regions[0].stack_size);
    } else {
        kpanic("FATAL: No cartridges loaded.\n");
    }
}