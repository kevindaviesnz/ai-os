#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

/* THE FIX: Initializing to non-zero forces these into .data, preventing .bss stripping! */
static uint8_t  fs_buffer[IPC_PAYLOAD_MAX_SIZE] = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1}; 
static uint32_t fs_size = 99;

void fs_handler(os_message_t *msg);

void _start(void) {
    fs_size = 0; /* Reset on boot */

    __asm__ volatile("mov x0, %0\n\t" "adr x1, fs_handler\n\t" "mov x8, %1\n\t" "svc 0\n\t" 
                     :: "i"(SYS_MOD_FS), "i"(SYS_MODULE_REGISTER) : "x0", "x1", "x8");
    
    __asm__ volatile("mov x8, %0\n\t" "svc 0\n\t" :: "i"(SYS_INIT_DONE) : "x8");
    
    while(1) { __asm__ volatile("wfi"); }
}

void fs_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_FS_WRITE) {
        fs_size = (msg->length <= IPC_PAYLOAD_MAX_SIZE) ? msg->length : IPC_PAYLOAD_MAX_SIZE;
        for(uint32_t i = 0; i < fs_size; i++) {
            fs_buffer[i] = msg->payload[i];
        }

        os_message_t ack = {0};
        ack.target_id = SYS_MOD_SHELL;
        ack.type = IPC_TYPE_SYS_ACK;
        ack.length = 0;
        __asm__ volatile("mov x1, %0\n\t" "mov x8, %1\n\t" "svc 0\n\t" 
                         :: "r"(&ack), "i"(SYS_IPC_SEND) : "x1", "x8");

    } else if (msg->type == IPC_TYPE_FS_READ) {
        os_message_t reply = {0};
        reply.target_id = SYS_MOD_SHELL;
        reply.type = IPC_TYPE_FS_READ; 
        reply.length = fs_size;
        for(uint32_t i = 0; i < fs_size; i++) {
            reply.payload[i] = fs_buffer[i];
        }
        __asm__ volatile("mov x1, %0\n\t" "mov x8, %1\n\t" "svc 0\n\t" 
                         :: "r"(&reply), "i"(SYS_IPC_SEND) : "x1", "x8");
    }
    
    __asm__ volatile("mov x8, %0\n\t" "svc 0\n\t" :: "i"(SYS_HANDLER_DONE));
}
