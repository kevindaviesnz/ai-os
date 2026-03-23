# Architecting a Hardware-Isolated ARM64 Microkernel: A Capability-Based Approach

**Abstract**
This paper details the architecture and implementation of a custom, bare-metal L4-style microkernel for the ARMv8-A (AArch64) architecture. Designed from absolute reset, the system prioritizes hardware-enforced security boundaries, strict principle-of-least-privilege execution, and capability-based inter-process communication (IPC). By leveraging the ARM Memory Management Unit (MMU) and the Generic Interrupt Controller (GICv2), the kernel successfully isolates unprivileged user-space (EL0) modules while maintaining deterministic, asynchronous message routing.

---

### 1. Introduction
Modern operating system design often struggles to balance raw performance with rigorous security. Monolithic kernels run massive amounts of code—including device drivers and file systems—in the highest privilege ring, creating a sprawling attack surface. 

This project explores a strict microkernel approach on the ARM64 architecture. The kernel is reduced to an absolute minimum: memory management, interrupt routing, and IPC dispatching. All other logic, including basic I/O (like the Shell), is pushed into unprivileged User Space (EL0). If a user-space module crashes or is compromised, the hardware prevents it from taking down the system.

### 2. Architectural Foundations

#### 2.1 Exception Level (EL) Topology
The system utilizes two primary ARMv8-A Exception Levels:
* **EL1 (Kernel Space):** Operates with full access to system registers, hardware peripherals (UART, GIC), and the MMU translation tables.
* **EL0 (User Space):** Operates in an unprivileged, restricted state. Memory access is strictly governed by the MMU, and hardware peripherals cannot be addressed directly.

To handle modern boot environments (like QEMU or physical hardware booting in Hypervisor mode), the kernel features an automatic EL2-to-EL1 drop sequence, reconfiguring `HCR_EL2` and `CNTHCTL_EL2` to ensure the physical timer and virtual environments are correctly mapped before execution begins.

#### 2.2 Memory Management & Hardware Isolation
Security in this microkernel is mathematically enforced by the MMU using a 4KB page granularity across a multi-level translation table (L1-L3).
* **W^X Enforcement:** Kernel memory is mapped with strict Write XOR Execute permissions.
* **User Space Sandbox:** EL0 memory is mapped with `PXN=1` (Privileged Execute-Never), preventing the kernel from accidentally executing user code (Confused Deputy mitigation). EL0 `.text` segments are mapped as `AP=11` (Read-Only at all levels) to physically prevent self-modifying code attacks.
* **Guard Pages:** The EL0 stack is protected by an intentional translation fault boundary (an unmapped descriptor) immediately below the stack base, ensuring stack overflows result in immediate process termination rather than silent memory corruption.

### 3. Capability-Based IPC
Because EL0 modules cannot access hardware or other modules directly, all communication must pass through the Kernel's IPC Dispatcher.

#### 3.1 The Dispatcher and Mailboxes
The IPC subsystem uses a mailbox queues approach. Modules communicate using a standardized `os_message_t` structure containing a target ID, message type, and payload. The kernel routes these messages asynchronously, allowing the system to remain highly responsive.

#### 3.2 The Capability Matrix
To prevent arbitrary inter-module interference, routing is governed by a static Capability Matrix locked in the kernel's `.rodata` section. If Module A attempts to send a message to Module B, the kernel checks the matrix. If the `IPC_CAP_SEND` bit is not set, the message is dropped and `IPC_ERR_DENIED` is returned. Because this matrix is in Read-Only memory, it is immune to runtime tampering.

### 4. The System Call (SVC) Boundary
The transition from unprivileged EL0 to privileged EL1 is the most critical security boundary in the system. User-space modules trigger a Synchronous Exception using the `svc` instruction.

#### 4.1 Strict Identity Injection
A common vulnerability in IPC design is trusting user-supplied sender identities. In this microkernel, the EL0 module does *not* provide its own sender ID. Instead, upon trapping the `svc` call, the kernel injects the known identity of the executing module (e.g., `SYS_MOD_SHELL`) before passing the message to the dispatcher. Identity forgery is architecturally impossible.

#### 4.2 Pointer Validation and Overflow Mitigation
When an EL0 module passes a pointer to an `os_message_t` struct via the `svc` interface, the kernel must validate it before dereferencing. The `is_valid_el0_pointer` function mathematically ensures the memory falls within the allowed EL0 stack or `.text` boundaries. Crucially, this check includes a strict integer overflow guard (`ptr + size < ptr`) to prevent pointer arithmetic bypass attacks.

#### 4.3 Context Scrubbing
Upon returning to User Space (`eret`), the kernel explicitly zeroes all General Purpose Registers (`x0-x30`). This prevents the leakage of kernel stack addresses or memory layouts, neutralizing Address Space Layout Randomization (KASLR) bypass vectors.

### 5. Interrupt Pipeline and Asynchrony
The kernel utilizes the GICv2 (Generic Interrupt Controller) to handle asynchronous hardware events.
* **Preemption:** The ARM Generic Timer (`CNTP_TVAL_EL0`) is configured to fire a physical timer interrupt (PPI 30) every 10ms. 
* **State Preservation:** Upon any interrupt, the CPU vectors to EL1, saving a 272-byte frame encompassing all 31 GPRs, `ELR_EL1` (the return address), and `SPSR_EL1` (the processor state). This guarantees that EL0 applications can be preempted and resumed with zero state corruption.

### 6. Conclusion
The Phase 6 milestone demonstrates a fully functional, capability-driven microkernel. By enforcing rigid hardware boundaries, sanitizing the SVC interface, and maintaining strict control over IPC identity and routing, the system achieves a highly defensible posture against both buggy software and malicious exploit attempts. 

**Future Work:** Subsequent phases will focus on implementing a Round-Robin scheduler driven by the 10ms timer tick to support concurrent EL0 tasks, and the introduction of dynamic memory allocation syscalls (`mmap`/`brk` equivalents) to allow modules to request heap space at runtime.

