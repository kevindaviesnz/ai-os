#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

void shell_handler(os_message_t *msg);
void print_string(const char *str); /* Declare it here so the compiler is happy */

/* THE FIX: _start is officially back at the top of the file (Offset 0x0) */
void _start(void) {
    __asm__ volatile("mov x0, %0\n\t" "adr x1, shell_handler\n\t" "mov x8, %1\n\t" "svc 0\n\t" 
                     :: "i"(SYS_MOD_SHELL), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    print_string("\n\nWelcome to the Microkernel.\n");
    print_string("kevindavies > ");

    __asm__ volatile("mov x8, %0\n\t" "svc 0\n\t" :: "i"(SYS_INIT_DONE) : "x8");
    while(1) { __asm__ volatile("wfi"); }
}

/* Now we define the helper function safely below the entry point */
void print_string(const char *str) {
    while (*str) {
        os_message_t out = {0};
        out.target_id = SYS_MOD_UART;
        out.type = IPC_TYPE_CHAR_OUT;
        out.length = 1;
        out.payload[0] = *str++;
        __asm__ volatile("mov x1, %0\n\t" "mov x8, %1\n\t" "svc 0\n\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
}

void shell_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_CHAR_IN) {
        os_message_t out = {0};
        out.target_id = SYS_MOD_UART;
        out.type = IPC_TYPE_CHAR_OUT;
        out.length = 1;
        out.payload[0] = msg->payload[0];
        __asm__ volatile("mov x1, %0\n\t" "mov x8, %1\n\t" "svc 0\n\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
        
        if (msg->payload[0] == '\r') {
            print_string("\nkevindavies > ");
        }
    }
    __asm__ volatile("mov x8, %0\n\t" "svc 0\n\t" :: "i"(SYS_HANDLER_DONE));
}
