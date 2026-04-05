import sys, struct

if len(sys.argv) < 3:
    print("Usage: mkbundle.py <out.atkb> <mod1.atkm> <mod2.atkm> ...")
    sys.exit(1)

modules = []
for path in sys.argv[2:]:
    with open(path, 'rb') as f:
        modules.append(f.read())

# sizeof(bundle_header_t) = 4+4+4+4 + 8*8 = 80 bytes
HEADER_SIZE = 80

offset = HEADER_SIZE
index_data = b""
for m in modules:
    index_data += struct.pack('<II', offset, len(m))
    offset += len(m)

# Pad to 64 bytes (8 slots * 8 bytes each)
index_data = index_data.ljust(64, b'\x00')

with open(sys.argv[1], 'wb') as f:
    f.write(struct.pack('<IIII', 0x41544B42, 1, len(modules), 0))
    f.write(index_data)
    for m in modules:
        f.write(m)