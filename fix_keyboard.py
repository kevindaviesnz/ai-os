import os

# 1. Update UART driver to turn on the hardware RX interrupt switch!
with open("modules/uart/uart_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

#define UART0_DR   ((volatile uint32_t *)0x09000000)
#define UART0_IMSC ((volatile uint32_t *)0x09000038)

void uart_handler(os_message_t *msg);

void _start(void) {
    /* THE FIX: Tell the silicon to trigger an interrupt when a key is pressed! */
    *UART0_IMSC = (1 << 4); 

    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, uart_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_UART), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
                     
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    
    while(1) { __asm__ volatile("wfi"); }
}

void uart_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_CHAR_OUT) {
        for (uint32_t i = 0; i < msg->length; i++) {
            *UART0_DR = msg->payloadLBiRB;
        }
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))

# 2. Patch the Interrupt Controller to clear the hardware flag after reading
try:
    with open("src/gic.c", "r") as f:
        gic_content = f.read()
        
    if "0x09000044" not in gic_content:
        gic_content = gic_content.replace(
            "uint8_t c = (uint8_t)(*uart);",
            "uint8_t c = (uint8_t)(*uart);\n    *((volatile uint32_t *)0x09000044) = (1 << 4); /* Clear the RX flag so it doesn't loop forever! */"
        )
        with open("src/gic.c", "w") as f:
            f.write(gic_content)
except FileNotFoundError:
    pass

# 3. Patch Makefile to WAIT for you to connect before booting!
try:
    with open("Makefile", "r") as f:
        mk_content = f.read()

    if "nowait" in mk_content:
        mk_content = mk_content.replace("server,nowait", "server,wait")

    with open("Makefile", "w") as f:
        f.write(mk_content)
except FileNotFoundError:
    pass