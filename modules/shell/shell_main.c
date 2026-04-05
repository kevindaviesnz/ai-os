#include "../../include/os_types.h"
#include "../../include/os_dispatcher.h"

#define SYS_IPC_SEND         1
#define SYS_MODULE_REGISTER  3
#define SYS_INIT_DONE        4
#define SYS_HANDLER_DONE     5
#define SYS_UART_WRITE       6

void shell_handler(os_message_t *msg);
void print_string(const char *str);
void uart_putc(char c);
void handle_command(void);

static char cmd_buf[64];
static uint32_t cmd_len = 0;

void _start(void) {
    __asm__ volatile(
        "mov x0, %0\n\t"
        "adr x1, shell_handler\n\t"
        "mov x8, %1\n\t"
        "svc 0\n\t"
        :: "i"(SYS_MOD_SHELL), "i"(SYS_MODULE_REGISTER)
        : "x0", "x1", "x8"
    );

    print_string("\n\nWelcome to the Microkernel.\n");
    print_string("ai-os > ");

    __asm__ volatile(
        "mov x8, %0\n\t"
        "svc 0\n\t"
        :: "i"(SYS_INIT_DONE)
        : "x8"
    );

    while (1) {
        __asm__ volatile("wfi");
    }
}

/*
 * uart_putc:
 * Sends a single character to UART.
 * Converts '\n' -> "\r\n"
 */
void uart_putc(char c) {
    if (c == '\n') {
        char cr = '\r';
        __asm__ volatile(
            "mov x0, %0\n\t"
            "mov x1, 1\n\t"
            "mov x8, %1\n\t"
            "svc 0\n\t"
            :: "r"(&cr), "i"(SYS_UART_WRITE)
            : "x0", "x1", "x8"
        );
    }

    __asm__ volatile(
        "mov x0, %0\n\t"
        "mov x1, 1\n\t"
        "mov x8, %1\n\t"
        "svc 0\n\t"
        :: "r"(&c), "i"(SYS_UART_WRITE)
        : "x0", "x1", "x8"
    );
}

void print_string(const char *str) {
    while (*str) {
        uart_putc(*str++);
    }
}

static int str_eq(const char *a, const char *b) {
    while (*a && *b) {
        if (*a != *b) return 0;
        a++; b++;
    }
    return *a == *b;
}

void handle_command(void) {
    cmd_buf[cmd_len] = '\0';

    if (str_eq(cmd_buf, "help")) {
        print_string("\nCommands:\n");
        print_string("  help  - Show this help\n");
        print_string("  info  - Show system information\n");
    } else if (str_eq(cmd_buf, "info")) {
        print_string("\nATK Microkernel\n");
        print_string("Modules loaded: 3 (uart, shell, fs)\n");
    } else if (cmd_len > 0) {
        print_string("\nUnknown command: ");
        print_string(cmd_buf);
        print_string("\n");
    }

    cmd_len = 0;
}

void shell_handler(os_message_t *msg) {
    if (msg->type == IPC_TYPE_CHAR_IN) {
        uint8_t c = msg->payload[0];

        if (c == '\r' || c == '\n') {
            uart_putc('\n');              // move to next line properly
            handle_command();
            print_string("ai-os > ");
        } 
        else if (c == 127 || c == '\b') {
            if (cmd_len > 0) {
                cmd_len--;

                // visually erase last character
                uart_putc('\b');
                uart_putc(' ');
                uart_putc('\b');
            }
        } 
        else {
            if (cmd_len < 63) {
                cmd_buf[cmd_len++] = c;

                // echo character
                uart_putc(c);
            }
        }
    }

    __asm__ volatile(
        "mov x8, %0\n\t"
        "svc 0\n\t"
        :: "i"(SYS_HANDLER_DONE)
    );
}