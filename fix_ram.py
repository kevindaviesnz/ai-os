with open("Makefile", "r") as f:
    content = f.read()

# Install 1GB of virtual RAM (-m 1024M) into the motherboard!
if "-m 1024M" not in content:
    content = content.replace("-M virt,gic-version=2 ", "-M virt,gic-version=2 -m 1024M ")

with open("Makefile", "w") as f:
    f.write(content)
