import os

# 1. Revert the Shell back to an Interactive Prompt
with open("modules/shell/shell_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

void shell_handler(os_message_t *msg);

void print_string(const char *str) {
    while (*str) {
        os_message_t out = {0};
        out.target_id = SYS_MOD_UART;
        out.type = IPC_TYPE_CHAR_OUT;
        out.length = 1;
        out.payloadLB0RB = *str++;
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
}

void _start(void) {
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, shell_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_SHELL), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    print_string("\\n\\nWelcome to the Microkernel.\\n");
    print_string("kevindavies > ");

    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    while(1) { __asm__ volatile("wfi"); }
}

void shell_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_CHAR_IN) {
        /* Echo the character back to the screen so you can see what you type */
        os_message_t out = {0};
        out.target_id = SYS_MOD_UART;
        out.type = IPC_TYPE_CHAR_OUT;
        out.length = 1;
        out.payloadLB0RB = msg->payloadLB0RB;
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
        
        /* If the user hits Enter (Carriage Return), print a new prompt line */
        if (msg->payloadLB0RB == '\\r') {
            print_string("\\nkevindavies > ");
        }
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))

# 2. Patch the Makefile to route the serial port to a local TCP socket (Port 4444)
try:
    with open("Makefile", "r") as f:
        content = f.read()

    # Replace the standard output with a TCP socket server
    if "-nographic" in content:
        content = content.replace("-nographic", "-display none -serial tcp:127.0.0.1:4444,server,nowait")

    with open("Makefile", "w") as f:
        f.write(content)
except FileNotFoundError:
    print("Error: Makefile not found.")