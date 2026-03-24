with open("modules/uart/uart_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_MOD_UART         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

void uart_handler(os_message_t *msg); /* Forward Declaration */

/* MUST BE FIRST FUNCTION IN FILE - Offset 0x0 */
void _start(void) {
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, uart_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_UART), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    
    while(1) { __asm__ volatile("wfi"); }
}

void uart_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_CHAR_OUT) {
        volatile uint32_t *uart = (volatile uint32_t *)0x09000000;
        *uart = msg->payloadLB0RB;
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))

with open("modules/shell/shell_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_MOD_UART         1
#define SYS_MOD_SHELL        2
#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

void shell_handler(os_message_t *msg); /* Forward Declaration */

/* MUST BE FIRST FUNCTION IN FILE - Offset 0x0 */
void _start(void) {
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, shell_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_SHELL), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    os_message_t init_msg;
    init_msg.target_id = SYS_MOD_UART;
    init_msg.type = IPC_TYPE_CHAR_OUT;
    init_msg.length = 1;
    init_msg.payloadLB0RB = '>';
    __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "r"(&init_msg), "i"(SYS_IPC_SEND) : "x1", "x8");

    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    while(1) { __asm__ volatile("wfi"); }
}

void shell_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_SYS_ACK) {
        os_message_t out_msg;
        out_msg.target_id = SYS_MOD_UART;
        out_msg.type = IPC_TYPE_CHAR_OUT;
        out_msg.length = 1;
        out_msg.payloadLB0RB = '.';
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                         :: "r"(&out_msg), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))
