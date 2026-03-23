
# ARM64 Microkernel

> A secure, bare-metal ARM64 (AArch64) microkernel featuring hardware-enforced MMU isolation, capability-based IPC, and GICv2 interrupt routing. Boots from absolute reset to a preemptible EL0 user-space shell via a strict SVC interface with robust pointer validation.

This project demonstrates the foundational architecture of an L4-style microkernel built entirely from scratch for the AArch64 architecture. It successfully isolates unprivileged user-space applications from kernel memory using hardware mechanisms while facilitating secure, asynchronous inter-process communication.

## Core Features

* **Hardware-Enforced Isolation:** Active Memory Management Unit (MMU) separating Kernel (EL1) and User Space (EL0). Enforces `PXN` (Privileged Execute-Never) and `W^X` (Write XOR Execute) memory protections.
* **Capability-Based IPC:** Asynchronous, non-blocking message passing between modules. Communication rights are governed by an immutable, `.rodata`-locked Capability Matrix.
* **Preemptive Multitasking Foundation:** Configured ARM Generic Timer (PPI 30) providing a 10ms hardware heartbeat to safely preempt EL0 execution.
* **Secure System Call (SVC) Interface:** Strict boundary crossing mechanism. The kernel authenticates sender identity internally and mathematically validates all user-supplied pointers against buffer overflows and memory bounds.
* **Hardware Interrupt Pipeline:** GICv2 controller routing physical UART keystrokes and timer ticks, with a guaranteed 33-register context save/restore frame (including `ELR_EL1` and `SPSR_EL1`).

## Project Structure

```text
├── Makefile
├── linker.ld           # Memory layout, stack guards, and EL0/EL1 sectioning
├── src/
│   ├── boot.S          # Reset vector, EL2-to-EL1 drop, .bss zeroing, MMU enable
│   ├── vectors.S       # AArch64 Exception Vector Table (2KB aligned)
│   ├── mmu.c           # Page table initialization (L1-L3) and memory attributes
│   ├── gic.c           # GICv2 Distributor/CPU Interface and IRQ handler
│   ├── timer.c         # ARM Generic Timer (CNTP_TVAL_EL0) initialization
│   ├── dispatcher.c    # IPC capability matrix and mailbox queue management
│   ├── syscall.c       # SVC exception decoding and pointer validation
│   ├── kernel.c        # EL1 Kernel entry, subsystem init, and jump_to_el0
│   └── shell.c         # EL0 User Space application and IPC wrappers
└── include/
    ├── os_types.h      # Core IPC message structures and constants
    └── os_dispatcher.h # Dispatcher function prototypes
```

## Security Invariants

This microkernel was designed with a "secure-by-default" philosophy, satisfying strict architectural audits:
1. **No Implicit Trust:** EL0 modules cannot spoof their sender identity. The kernel injects the `sender_id` during the SVC trap.
2. **Defensive Memory Mapping:** The EL0 stack is protected by an unmapped guard page to catch stack overflows via Translation Faults. EL0 `.text` is mapped as `AP=11` (Read-Only) to prevent self-modifying code.
3. **Register Scrubbing:** All General Purpose Registers (GPRs) are explicitly zeroed prior to the `eret` transition into User Space to prevent Kernel memory layout leaks (KASLR bypass mitigation).

## Prerequisites

To build and run this project, you need an ARM64 GCC toolchain and QEMU.

If compiling natively on an ARM64 Linux machine (like Debian/Ubuntu on Apple Silicon):
```bash
sudo apt-get install build-essential qemu-system-arm
```
*(Note: If cross-compiling from x86, you will need to update the `CC` variable in the `Makefile` to `aarch64-linux-gnu-gcc`)*

## Build & Run

The project is configured to run on the QEMU `virt` machine targeting a Cortex-A53 CPU.

```bash
# Compile the kernel and launch the QEMU emulator
make clean && make run
```

Upon a successful boot, you will see the Kernel initialization sequence, followed by a drop into the unprivileged User Space shell:

```text
[KERNEL] Microkernel Phase 6 Booted.
[KERNEL] Dropping to EL0 User Space...
>........
```
* **Type on your keyboard:** Characters will be routed via hardware interrupt to the kernel, passed to the EL0 shell via IPC, and echoed back.
* **Watch the dots:** The timer interrupt fires every 10ms, dropping a tick message into the shell's mailbox every 1 second.

**To exit QEMU:** Press `Ctrl + A`, then release and press `X`.

## Architecture Roadmap & Future Work

* **Phase 7:** Implement a true Round-Robin Scheduler using the timer heartbeat to switch contexts between multiple EL0 applications.
* **Phase 8:** Introduce dynamic memory allocation (a `brk` or `mmap` equivalent) for EL0 via the SVC interface.
* **Phase 9:** Enable SMP (Symmetric Multiprocessing) and introduce hardware memory barriers around the Dispatcher mailboxes.
```