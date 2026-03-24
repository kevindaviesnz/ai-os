#include "../include/os_types.h"
#include "../include/os_dispatcher.h"

#define SYS_IPC_SEND    1
#define SYS_IPC_RECEIVE 2

/* Using .el0_user_text to dodge the linker wildcard! */
__attribute__((section(".el0_user_text")))
int sys_ipc_receive(os_message_t *msg) {
    register uint64_t x0 __asm__("x0") = (uint64_t)msg;
    register uint64_t x8 __asm__("x8") = SYS_IPC_RECEIVE;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x8) : "memory");
    return x0;
}

__attribute__((section(".el0_user_text")))
int sys_ipc_send(uint32_t target_id, os_message_t *msg) {
    register uint64_t x0 __asm__("x0") = target_id;
    register uint64_t x1 __asm__("x1") = (uint64_t)msg;
    register uint64_t x8 __asm__("x8") = SYS_IPC_SEND;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x8) : "memory");
    return x0;
}

__attribute__((section(".el0_user_text")))
void shell_main(void) {
    os_message_t msg;
    
    msg.target_id = SYS_MOD_UART;
    msg.type = IPC_TYPE_CHAR_OUT;
    msg.length = 1;
    *msg.payload = '>';
    sys_ipc_send(SYS_MOD_UART, &msg);

    while (1) {
        if (sys_ipc_receive(&msg) == 0) {
            if (msg.type == IPC_TYPE_CHAR_IN) {
                msg.target_id = SYS_MOD_UART;
                msg.type = IPC_TYPE_CHAR_OUT;
                sys_ipc_send(SYS_MOD_UART, &msg);
            } else if (msg.type == IPC_TYPE_SYS_ACK) {
                msg.target_id = SYS_MOD_UART;
                msg.type = IPC_TYPE_CHAR_OUT;
                *msg.payload = '.';
                sys_ipc_send(SYS_MOD_UART, &msg);
            }
        } else {
            __asm__ volatile("wfi");
        }
    }
}
