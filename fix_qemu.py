with open("Makefile", "r") as f:
    content = f.read()

# Force QEMU to use the GICv2 hardware chip
content = content.replace("-M virt ", "-M virt,gic-version=2 ")

with open("Makefile", "w") as f:
    f.write(content)
