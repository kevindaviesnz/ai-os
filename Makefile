CC = gcc
CFLAGS = -Wall -Wextra -ffreestanding -mgeneral-regs-only -nostdlib -fno-builtin
LDFLAGS = -T linker.ld -nostdlib

SRCS_ASM = src/boot.S src/vectors.S
SRCS_C = src/kernel.c src/dispatcher.c src/mmu.c src/gic.c src/timer.c src/syscall.c src/shell.c
OBJS = boot.o vectors.o kernel.o dispatcher.o mmu.o gic.o timer.o syscall.o shell.o

all: os.elf

%.o: src/%.S
	$(CC) $(CFLAGS) -c $< -o $@

%.o: src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

os.elf: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

run: os.elf
	qemu-system-aarch64 -M virt -cpu cortex-a53 -nographic -kernel os.elf

clean:
	rm -f *.o *.elf
