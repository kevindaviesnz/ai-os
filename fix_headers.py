import os

# 1. Fully populate os_dispatcher.h with the System Module IDs
with open("include/os_dispatcher.h", "w") as f:
    code = """#ifndef OS_DISPATCHER_H
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
"""
    f.write(code)

# 2. Scrub the redundant local definitions from the C files to prevent compiler warnings
files_to_clean = ["modules/shell/shell_main.c", "modules/fs/fs_main.c", "src/kernel.c", "modules/uart/uart_main.c"]

for filepath in files_to_clean:
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read()
        
        # Remove the localized defines
        content = content.replace("#define SYS_MOD_UART         1\n", "")
        content = content.replace("#define SYS_MOD_SHELL        2\n", "")
        content = content.replace("#define SYS_MOD_FS           3\n", "")
        content = content.replace("#define SYS_MOD_SHELL 2\n", "")
        
        with open(filepath, "w") as f:
            f.write(content)