import os

# 1. Fix Shell Cartridge
with open("modules/shell/shell_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

/* THE FIX: Initializing to -1 forces this into the .data section, preventing .bss stripping! */
int state = -1;

void shell_handler(os_message_t *msg);

void _start(void) {
    state = 0; /* Reset state on boot */
    
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, shell_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_SHELL), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
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
        state = 1;
        os_message_t req = {0};
        req.target_id = SYS_MOD_FS;
        req.type = IPC_TYPE_FS_READ;
        req.length = 0;
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&req), "i"(SYS_IPC_SEND) : "x1", "x8");
        
    } else if (state == 1 && msg->type == IPC_TYPE_FS_READ) {
        state = 2;
        /* THE FIX: Send the whole string in one message, otherwise we overflow the UART mailbox! */
        os_message_t out = {0};
        out.target_id = SYS_MOD_UART;
        out.type = IPC_TYPE_CHAR_OUT;
        out.length = msg->length;
        for (uint32_t i = 0; i < msg->length; i++) {
            out.payloadLBiRB = msg->payloadLBiRB;
        }
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))

# 2. Fix FS Cartridge
with open("modules/fs/fs_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

/* THE FIX: Initializing to non-zero forces these into .data, preventing .bss stripping! */
static uint8_t  fs_bufferLBIPC_PAYLOAD_MAX_SIZERB = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1}; 
static uint32_t fs_size = 99;

void fs_handler(os_message_t *msg);

void _start(void) {
    fs_size = 0; /* Reset on boot */

    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, fs_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_FS), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    
    while(1) { __asm__ volatile("wfi"); }
}

void fs_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_FS_WRITE) {
        fs_size = (msg->length <= IPC_PAYLOAD_MAX_SIZE) ? msg->length : IPC_PAYLOAD_MAX_SIZE;
        for(uint32_t i = 0; i < fs_size; i++) {
            fs_bufferLBiRB = msg->payloadLBiRB;
        }

        os_message_t ack = {0};
        ack.target_id = SYS_MOD_SHELL;
        ack.type = IPC_TYPE_SYS_ACK;
        ack.length = 0;
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                         :: "r"(&ack), "i"(SYS_IPC_SEND) : "x1", "x8");

    } else if (msg->type == IPC_TYPE_FS_READ) {
        os_message_t reply = {0};
        reply.target_id = SYS_MOD_SHELL;
        reply.type = IPC_TYPE_FS_READ; 
        reply.length = fs_size;
        for(uint32_t i = 0; i < fs_size; i++) {
            reply.payloadLBiRB = fs_bufferLBiRB;
        }
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                         :: "r"(&reply), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
    
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))