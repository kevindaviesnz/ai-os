CC = aarch64-elf-gcc
LD = aarch64-elf-ld
OBJCOPY = aarch64-elf-objcopy

CFLAGS = -Wall -Wextra -ffreestanding -mgeneral-regs-only -nostdlib -fno-builtin
LDFLAGS = -T linker.ld -nostdlib

OBJS = src/boot.o src/vectors.o src/kernel.o src/dispatcher.o src/mmu.o src/gic.o src/timer.o src/syscall.o src/loader.o src/cartridge_verify.o src/kpanic.o

all: os.elf os.atkb

%.o: %.S
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.c
	$(CC) $(CFLAGS) -DATK_STUB_VERIFY -c $< -o $@

os.elf: $(OBJS)
	$(LD) $(LDFLAGS) $(OBJS) -o os.elf

# --- Module Compilation (Position Independent Code for Microkernel) ---
modules/uart/uart_main.o: modules/uart/uart_main.c
	$(CC) $(CFLAGS) -fPIE -c $< -o $@

uart.bin: modules/uart/uart_main.o
	$(LD) -Ttext 0x0 -nostdlib --build-id=none $< -o uart.elf
	$(OBJCOPY) -O binary uart.elf uart.bin

uart.atkm: uart.bin
	python3 tools/mkcartridge.py uart.bin uart.elf uart.atkm 1 4096

modules/shell/shell_main.o: modules/shell/shell_main.c
	$(CC) $(CFLAGS) -fPIE -c $< -o $@

shell.bin: modules/shell/shell_main.o
	$(LD) -Ttext 0x0 -nostdlib --build-id=none $< -o shell.elf
	$(OBJCOPY) -O binary shell.elf shell.bin

shell.atkm: shell.bin
	python3 tools/mkcartridge.py shell.bin shell.elf shell.atkm 2 8192

modules/fs/fs_main.o: modules/fs/fs_main.c
	$(CC) $(CFLAGS) -fPIE -c $< -o $@

fs.bin: modules/fs/fs_main.o
	$(LD) -Ttext 0x0 -nostdlib --build-id=none $< -o fs.elf
	$(OBJCOPY) -O binary fs.elf fs.bin

fs.atkm: fs.bin
	python3 tools/mkcartridge.py fs.bin fs.elf fs.atkm 3 8192

# --- Bundle Creation ---
os.atkb: uart.atkm shell.atkm fs.atkm
	python3 tools/mkbundle.py os.atkb uart.atkm shell.atkm fs.atkm

clean:
	rm -f src/*.o modules/*/*.o *.elf *.bin *.atkm *.atkb

run: all
	qemu-system-aarch64 -M virt,gic-version=2 -m 1024M -cpu cortex-a53 -display none -serial tcp:127.0.0.1:4444,server,wait -kernel os.elf -device loader,file=os.atkb,addr=0x50000000,force-raw=on