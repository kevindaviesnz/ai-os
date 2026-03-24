import os

with open("modules/shell/shell_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

int state = 0;

void shell_handler(os_message_t *msg);

/* MUST BE FIRST FUNCTION IN FILE - Offset 0x0 */
void _start(void) {
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, shell_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_SHELL), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    /* Autonomous Test Step 1: Write "HELLO" to the RAM-disk! */
    os_message_t init_msg = {0};
    init_msg.target_id = SYS_MOD_FS;
    init_msg.type = IPC_TYPE_FS_WRITE;
    init_msg.length = 5;
    init_msg.payloadLB0RB = 'H';
    init_msg.payloadLB1RB = 'E';
    init_msg.payloadLB2RB = 'L';
    init_msg.payloadLB3RB = 'L';
    init_msg.payloadLB4RB = 'O';
    
    __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "r"(&init_msg), "i"(SYS_IPC_SEND) : "x1", "x8");

    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    while(1) { __asm__ volatile("wfi"); }
}

void shell_handler(os_message_t *msg) {
    if (state == 0 && msg->type == IPC_TYPE_SYS_ACK) {
        /* Autonomous Test Step 2: FS acknowledged the write. Now send a Read Request! */
        state = 1;
        os_message_t req = {0};
        req.target_id = SYS_MOD_FS;
        req.type = IPC_TYPE_FS_READ;
        req.length = 0;
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&req), "i"(SYS_IPC_SEND) : "x1", "x8");
        
    } else if (state == 1 && msg->type == IPC_TYPE_FS_READ) {
        /* Autonomous Test Step 3: FS returned the data. Forward it byte-by-byte to UART! */
        state = 2;
        for (uint32_t i = 0; i < msg->length; i++) {
            os_message_t out = {0};
            out.target_id = SYS_MOD_UART;
            out.type = IPC_TYPE_CHAR_OUT;
            out.length = 1;
            out.payloadLB0RB = msg->payloadLBiRB;
            __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
        }
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))