CC = gcc
CFLAGS = -Wall -Wextra -ffreestanding -mgeneral-regs-only -nostdlib -fno-builtin
LDFLAGS = -T linker.ld -nostdlib

OBJS = src/boot.o src/vectors.o src/kernel.o src/dispatcher.o src/mmu.o src/gic.o src/timer.o src/syscall.o src/loader.o src/cartridge_verify.o src/kpanic.o

all: os.elf os.atkb

%.o: %.S
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.c
	$(CC) $(CFLAGS) -DATK_STUB_VERIFY -c $< -o $@

os.elf: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o os.elf

# --- Cartridge Compilation ---
modules/uart/uart_main.o: modules/uart/uart_main.c
	$(CC) $(CFLAGS) -fPIE -c $< -o $@

uart.bin: modules/uart/uart_main.o
	ld -Ttext 0x0 -nostdlib --build-id=none $< -o uart.elf
	objcopy -O binary uart.elf uart.bin

uart.atkm: uart.bin tools/mkcartridge
	./tools/mkcartridge uart.bin uart.atkm 1 4096

modules/shell/shell_main.o: modules/shell/shell_main.c
	$(CC) $(CFLAGS) -fPIE -c $< -o $@

shell.bin: modules/shell/shell_main.o
	ld -Ttext 0x0 -nostdlib --build-id=none $< -o shell.elf
	objcopy -O binary shell.elf shell.bin

shell.atkm: shell.bin tools/mkcartridge
	./tools/mkcartridge shell.bin shell.atkm 2 8192
	gcc -Wall -Wextra -ffreestanding -mgeneral-regs-only -nostdlib -fno-builtin -fPIE -c modules/fs/fs_main.c -o modules/fs/fs_main.o
	ld -Ttext 0x0 -nostdlib --build-id=none modules/fs/fs_main.o -o fs.elf
	objcopy -O binary fs.elf fs.bin
	./tools/mkcartridge fs.bin fs.atkm 3 8192

os.atkb: uart.atkm shell.atkm fs.atkm tools/mkbundle
	./tools/mkbundle os.atkb uart.atkm shell.atkm fs.atkm

clean:
	rm -f src/*.o modules/*/*.o *.elf *.bin *.atkm *.atkb

run: all
	qemu-system-aarch64 -M virt,gic-version=2 -m 1024M -cpu cortex-a53 -display none -serial tcp:127.0.0.1:4444,server,wait -kernel os.elf -device loader,file=os.atkb,addr=0x50000000
