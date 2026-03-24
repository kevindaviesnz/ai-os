import os

# 1. Update the Shared Header (WARNING-12, BLOCKER-32)
with open("include/os_dispatcher.h", "w") as f:
    code = """#ifndef OS_DISPATCHER_H
#define OS_DISPATCHER_H

#include "os_types.h"

#define MODULE_COUNT         4
#define IPC_PAYLOAD_MAX_SIZE 16

#define IPC_ERR_DENIED   1
#define IPC_ERR_INVALID  2

/* Inter-Process Communication Types */
#define IPC_TYPE_CHAR_OUT  1
#define IPC_TYPE_CHAR_IN   2
#define IPC_TYPE_SYS_ACK   3
#define IPC_TYPE_FS_WRITE  0x03
#define IPC_TYPE_FS_READ   0x04

typedef struct {
    uint32_t target_id;
    uint32_t type;
    uint32_t length;
    uint8_t  payload[IPC_PAYLOAD_MAX_SIZE];
} os_message_t;

int ipc_send(uint32_t sender_id, const os_message_t *msg);

#endif
"""
    f.write(code)

# 2. Patch the Kernel to enforce the Capability Matrix (BLOCKER-32)
with open("src/syscall.c", "r") as f:
    syscall_content = f.read()

# Isolate the old ipc_send and replace it with the matrix-enforced version
old_ipc_send = """int ipc_send(uint32_t sender_id, const os_message_t *msg) {
    (void)sender_id;
    uint32_t target_id = msg->target_id;
    if (target_id >= 8) return 2; 
    if (module_contexts[target_id].in_handler || module_contexts[target_id].has_msg) return 2;
    
    module_contexts[target_id].mailbox.target_id = msg->target_id;
    module_contexts[target_id].mailbox.type = msg->type;
    module_contexts[target_id].mailbox.length = msg->length;
    for(int i=0; i<4; i++) {
        module_contexts[target_id].mailbox.payload[i] = msg->payload[i];
    }
    
    module_contexts[target_id].has_msg = 1;
    return 0; 
}"""

new_ipc_send = """const uint8_t capability_matrix[MODULE_COUNT][MODULE_COUNT] = {
    /* KERNEL  UART  SHELL  FS  */
    {  1,      1,    1,     1  },  /* KERNEL */
    {  1,      0,    1,     0  },  /* UART   */
    {  0,      1,    0,     1  },  /* SHELL  */
    {  0,      0,    1,     0  },  /* FS     */
};

int ipc_send(uint32_t sender_id, const os_message_t *msg) {
    uint32_t target_id = msg->target_id;
    if (sender_id >= MODULE_COUNT || target_id >= MODULE_COUNT) return IPC_ERR_INVALID; 
    if (!capability_matrix[sender_id][target_id]) return IPC_ERR_DENIED;
    
    if (module_contexts[target_id].in_handler || module_contexts[target_id].has_msg) return IPC_ERR_INVALID;
    
    module_contexts[target_id].mailbox.target_id = msg->target_id;
    module_contexts[target_id].mailbox.type = msg->type;
    module_contexts[target_id].mailbox.length = msg->length;
    
    /* Safely copy bytes up to MAX_SIZE */
    for(int i=0; i<IPC_PAYLOAD_MAX_SIZE; i++) {
        module_contexts[target_id].mailbox.payload[i] = msg->payload[i];
    }
    
    module_contexts[target_id].has_msg = 1;
    return 0; 
}"""

# Safely replace the function
if old_ipc_send in syscall_content:
    syscall_content = syscall_content.replace(old_ipc_send, new_ipc_send)
    with open("src/syscall.c", "w") as f:
        f.write(syscall_content)

# 3. Generate the Hardened FS Cartridge (BLOCKER-30, BLOCKER-31, WARNING-11)
os.makedirs("modules/fs", exist_ok=True)
with open("modules/fs/fs_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_MOD_UART         1
#define SYS_MOD_SHELL        2
#define SYS_MOD_FS           3

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

/* Safely sized RAM-disk storage */
static uint8_t  fs_buffer[IPC_PAYLOAD_MAX_SIZE]; 
static uint32_t fs_size = 0;

void fs_handler(os_message_t *msg);

void _start(void) {
    __asm__ volatile("mov x0, %0\\n\\t" "adr x1, fs_handler\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                     :: "i"(SYS_MOD_FS), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_INIT_DONE) : "x8");
    
    while(1) { __asm__ volatile("wfi"); }
}

void fs_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_FS_WRITE) {
        /* Bound-checked storage */
        fs_size = (msg->length <= IPC_PAYLOAD_MAX_SIZE) ? msg->length : IPC_PAYLOAD_MAX_SIZE;
        for(int i = 0; i < fs_size; i++) {
            fs_buffer[i] = msg->payload[i];
        }

        /* Zero-initialized ACK */
        os_message_t ack = {0};
        ack.target_id = SYS_MOD_SHELL;
        ack.type = IPC_TYPE_SYS_ACK;
        ack.length = 0;
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                         :: "r"(&ack), "i"(SYS_IPC_SEND) : "x1", "x8");

    } else if (msg->type == IPC_TYPE_FS_READ) {
        /* Zero-initialized Reply */
        os_message_t reply = {0};
        reply.target_id = SYS_MOD_SHELL;
        reply.type = IPC_TYPE_FS_READ; 
        reply.length = fs_size;
        for(int i = 0; i < fs_size; i++) {
            reply.payload[i] = fs_buffer[i];
        }
        __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" 
                         :: "r"(&reply), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
    
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code)