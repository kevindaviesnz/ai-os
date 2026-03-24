.section .text.boot
.global _start

.equ TCR_T0SZ,      25
.equ TCR_IRGN0_WB,  (1 << 8)
.equ TCR_ORGN0_WB,  (1 << 10)
.equ TCR_SH0_IS,    (3 << 12)
.equ TCR_EPD1,      (1 << 23)
.equ TCR_VALUE,     (TCR_T0SZ | TCR_IRGN0_WB | TCR_ORGN0_WB | TCR_SH0_IS | TCR_EPD1)

.equ MAIR_VALUE,    0xFF00

.equ SCTLR_M,       (1 << 0)
.equ SCTLR_C,       (1 << 2)
.equ SCTLR_I,       (1 << 12)
.equ SCTLR_VALUE,   (SCTLR_M | SCTLR_C | SCTLR_I)

_start:
    mrs     x0, mpidr_el1
    and     x0, x0, #0xFF
    cbnz    x0, .Lspin

    /* Detect and handle EL2 boot environment (BLOCKER-16) */
    mrs     x0, CurrentEL
    lsr     x0, x0, #2
    cmp     x0, #2
    bne     .Lel1_boot

.Lel2_config:
    /* Enable EL1 access to physical timer */
    mrs     x0, cnthctl_el2
    orr     x0, x0, #3          /* EL1PCTEN | EL1PCEN */
    msr     cnthctl_el2, x0

    msr     cntvoff_el2, xzr

    mov     x0, #(1 << 31)      /* RW: EL1 runs in AArch64 */
    msr     hcr_el2, x0

    /* Drop from EL2 to EL1 via ERET */
    mov     x0, #0x3C5          /* SPSR: EL1h, DAIF masked, AArch64 */
    msr     spsr_el2, x0
    adr     x0, .Lel1_boot
    msr     elr_el2, x0
    eret

.Lel1_boot:
    ldr     x0, =_stack_top
    mov     sp, x0

    ldr     x0, =_bss_start
    ldr     x1, =_bss_end
    cmp     x0, x1
    beq     .Lbss_done
.Lbss_loop:
    str     xzr, [x0], #8
    cmp     x0, x1
    blo     .Lbss_loop
.Lbss_done:

    bl      mmu_init_tables

    tlbi    vmalle1
    dsb     sy
    isb
    ic      iallu
    dsb     sy
    isb

    ldr     x0, =_ttb_l1
    msr     ttbr0_el1, x0
    ldr     x0, =TCR_VALUE
    msr     tcr_el1, x0
    ldr     x0, =MAIR_VALUE
    msr     mair_el1, x0
    isb

    mrs     x0, sctlr_el1
    ldr     x1, =SCTLR_VALUE
    orr     x0, x0, x1
    msr     sctlr_el1, x0
    isb

    ldr     x0, =_vectors
    msr     vbar_el1, x0

    msr     daifclr, #2

    bl      kernel_main

.Lkernel_returned:
    mov     x0, #0xDEAD
    movk    x0, #0xC0DE, lsl #16
    wfe
    b       .Lkernel_returned

.Lspin:
    wfe
    b       .Lspin

.global jump_to_el0
jump_to_el0:
    /* x0 contains the address of the EL0 entry point */
    msr     elr_el1, x0

    ldr     x0, =_el0_stack_top
    msr     sp_el0, x0

    mov     x0, #0
    msr     spsr_el1, x0    /* EL0t, DAIF unmasked */

    /* Scrub registers to prevent kernel info leaks (WARNING-06) */
    mov     x0,  #0
    mov     x1,  #0
    mov     x2,  #0
    mov     x3,  #0
    mov     x4,  #0
    mov     x5,  #0
    mov     x6,  #0
    mov     x7,  #0
    mov     x8,  #0
    mov     x9,  #0
    mov     x10, #0
    mov     x11, #0
    mov     x12, #0
    mov     x13, #0
    mov     x14, #0
    mov     x15, #0
    mov     x16, #0
    mov     x17, #0
    mov     x18, #0
    mov     x19, #0
    mov     x20, #0
    mov     x21, #0
    mov     x22, #0
    mov     x23, #0
    mov     x24, #0
    mov     x25, #0
    mov     x26, #0
    mov     x27, #0
    mov     x28, #0
    mov     x29, #0
    mov     x30, #0

    eret

.global launch_cartridge
launch_cartridge:
    /* x0 = elr (Entry Point / Code Base) */
    /* x1 = sp_el0 (Stack Top) */
    
    msr     elr_el1, x0
    msr     sp_el0, x1

    mov     x2, #0
    msr     spsr_el1, x2    /* EL0t, DAIF unmasked */

    /* BLOCKER-23: Scrub all GPRs before dropping to EL0 */
    mov     x0,  #0
    mov     x1,  #0
    mov     x2,  #0
    mov     x3,  #0
    mov     x4,  #0
    mov     x5,  #0
    mov     x6,  #0
    mov     x7,  #0
    mov     x8,  #0
    mov     x9,  #0
    mov     x10, #0
    mov     x11, #0
    mov     x12, #0
    mov     x13, #0
    mov     x14, #0
    mov     x15, #0
    mov     x16, #0
    mov     x17, #0
    mov     x18, #0
    mov     x19, #0
    mov     x20, #0
    mov     x21, #0
    mov     x22, #0
    mov     x23, #0
    mov     x24, #0
    mov     x25, #0
    mov     x26, #0
    mov     x27, #0
    mov     x28, #0
    mov     x29, #0
    mov     x30, #0

    eret
