#include "../include/os_types.h"

extern void uart_print(const char *str);

int cartridge_verify(const uint8_t *cartridge, uint32_t size, const uint8_t *pub_key) {
    (void)cartridge;
    (void)size;
    (void)pub_key;

#ifdef ATK_STUB_VERIFY
    return 0; /* IPC_OK - Development Override */
#else
    uart_print("ERR: Unsigned cartridge rejected in production build.\n");
    return -2; /* IPC_ERR_DENIED */
#endif
}
