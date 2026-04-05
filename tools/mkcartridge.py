import sys, struct

if len(sys.argv) < 6:
    print("Usage: mkcartridge.py <bin> <elf> <out> <id> <stack_size>")
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    data = f.read()

with open(sys.argv[2], 'rb') as f:
    elf = f.read()

e_phoff     = struct.unpack_from('<Q', elf, 32)[0]
e_phentsize = struct.unpack_from('<H', elf, 54)[0]
e_phnum     = struct.unpack_from('<H', elf, 56)[0]

total_mem_size = len(data)
for i in range(e_phnum):
    ph = e_phoff + i * e_phentsize
    p_type  = struct.unpack_from('<I', elf, ph)[0]
    if p_type == 1:  # PT_LOAD
        p_vaddr = struct.unpack_from('<Q', elf, ph + 16)[0]
        p_memsz = struct.unpack_from('<Q', elf, ph + 40)[0]
        end = p_vaddr + p_memsz
        if end > total_mem_size:
            total_mem_size = end

padded_data = data + b'\x00' * (total_mem_size - len(data))

header = struct.pack('<IIIIII', 0x41544B4D, 1, int(sys.argv[4]), len(padded_data), int(sys.argv[5]), 0)
header += b'\x00' * 64

with open(sys.argv[3], 'wb') as f:
    f.write(header + padded_data)