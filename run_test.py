import os

# 1. Generate the Autonomous Shell
os.makedirs("modules/shell", exist_ok=True)
with open("modules/shell/shell_main.c", "w") as f:
    code = """#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_MOD_UART         1
#define SYS_MOD_SHELL        2
#define SYS_MOD_FS           3

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5

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
    init_msg.payload = 'H';
    init_msg.payload = 'E';
    init_msg.payload = 'L';
    init_msg.payload = 'L';
    init_msg.payload = 'O';
    
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
        for (int i = 0; i < msg->length; i++) {
            os_message_t out = {0};
            out.target_id = SYS_MOD_UART;
            out.type = IPC_TYPE_CHAR_OUT;
            out.length = 1;
            out.payload = msg->payload[i];
            __asm__ volatile("mov x1, %0\\n\\t" "mov x8, %1\\n\\t" "svc 0\\n\\t" :: "r"(&out), "i"(SYS_IPC_SEND) : "x1", "x8");
        }
    }
    __asm__ volatile("mov x8, %0\\n\\t" "svc 0\\n\\t" :: "i"(SYS_HANDLER_DONE));
}
"""
    f.write(code)

# 2. Safely Patch the Makefile to compile and bundle the FS Cartridge
try:
    with open("Makefile", "r") as f:
        lines = f.readlines()

    with open("Makefile", "w") as f:
        for line in lines:
            # Append fs.atkm to the bundle command
            if "mkbundle" in line and "fs.atkm" not in line:
                line = line.replace("shell.atkm", "shell.atkm fs.atkm")
            
            f.write(line)
            
            # Inject FS build instructions immediately after the Shell build instructions
            if "mkcartridge shell.bin shell.atkm 2" in line and not any("fs_main.c" in l for l in lines):
                f.write("\tgcc -Wall -Wextra -ffreestanding -mgeneral-regs-only -nostdlib -fno-builtin -fPIE -c modules/fs/fs_main.c -o modules/fs/fs_main.o\n")
                f.write("\tld -Ttext 0x0 -nostdlib --build-id=none modules/fs/fs_main.o -o fs.elf\n")
                f.write("\tobjcopy -O binary fs.elf fs.bin\n")
                f.write("\t./tools/mkcartridge fs.bin fs.atkm 3 8192\n")
except FileNotFoundError:
    print("Error: Makefile not found. Are you in the ~/os_project directory?")