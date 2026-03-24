#ifndef OS_IPC_H
#define OS_IPC_H

#include "os_types.h"

#define SYS_MOD_KERNEL  0
#define SYS_MOD_UART    1
#define SYS_MOD_SHELL   2
#define MODULE_COUNT    3

STATIC_ASSERT(SYS_MOD_SHELL < MODULE_COUNT, shell_id_bounds);

#define IPC_TYPE_SYS_ACK     0x00
#define IPC_TYPE_CHAR_OUT    0x01
#define IPC_TYPE_CHAR_IN     0x02

#define IPC_PAYLOAD_MAX_SIZE 16

typedef struct {
    uint32_t sender_id; 
    uint32_t target_id;
    uint32_t type;
    uint32_t length;
    uint8_t  payload[IPC_PAYLOAD_MAX_SIZE];
} os_message_t;

#define IPC_MSG_VALID(msg) \
    ((msg) != 0 && \
     (msg)->length <= IPC_PAYLOAD_MAX_SIZE && \
     (msg)->target_id < MODULE_COUNT)

#define IPC_OK            0
#define IPC_ERR_FULL     -1
#define IPC_ERR_EMPTY    -2
#define IPC_ERR_DENIED   -3
#define IPC_ERR_INVALID  -4

#define MAILBOX_CAPACITY 8

typedef struct {
    uint32_t owner_id;
    os_message_t queue[MAILBOX_CAPACITY];
    uint32_t head;
    uint32_t tail;
    uint32_t count;
} os_mailbox_t;

#endif
