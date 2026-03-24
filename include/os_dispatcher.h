#ifndef OS_DISPATCHER_H
#define OS_DISPATCHER_H

#include "os_types.h"

/* System Module IDs */
#define SYS_MOD_KERNEL       0
#define SYS_MOD_UART         1
#define SYS_MOD_SHELL        2
#define SYS_MOD_FS           3

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
