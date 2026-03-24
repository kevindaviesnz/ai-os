with open("tools/mkcartridge.c", "w") as f:
    code = """#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define MAGIC_ATKM 0x41544B4D

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint32_t version;
    uint32_t module_id;
    uint32_t code_size;
    uint32_t stack_size;
    uint32_t reserved;
    uint8_t  signatureLB64RB;
} cartridge_header_t;

int main(int argc, char **argv) {
    if (argc != 5) {
        printf("Usage: %s <in.bin> <out.atkm> <module_id> <stack_size>\\n", argvLB0RB);
        return 1;
    }

    FILE *fin = fopen(argvLB1RB, "rb");
    FILE *fout = fopen(argvLB2RB, "wb");
    uint32_t mod_id = atoi(argvLB3RB);
    uint32_t stack_size = atoi(argvLB4RB);

    fseek(fin, 0, SEEK_END);
    uint32_t code_size = ftell(fin);
    fseek(fin, 0, SEEK_SET);

    cartridge_header_t hdr;
    memset(&hdr, 0, sizeof(hdr));
    hdr.magic = MAGIC_ATKM;
    hdr.version = 1;
    hdr.module_id = mod_id;
    hdr.code_size = code_size;
    hdr.stack_size = stack_size;

    fwrite(&hdr, sizeof(hdr), 1, fout);

    uint8_t *buffer = malloc(code_size);
    fread(buffer, 1, code_size, fin);
    fwrite(buffer, 1, code_size, fout);

    free(buffer);
    fclose(fin);
    fclose(fout);
    return 0;
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))

with open("tools/mkbundle.c", "w") as f:
    code = """#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define MAGIC_ATKB 0x41544B42

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint32_t version;
    uint32_t cartridge_count;
    uint32_t reserved;
    struct {
        uint32_t offset;
        uint32_t size;
    } indexLB8RB;
} bundle_header_t;

int main(int argc, char **argv) {
    if (argc < 3 || argc > 10) {
        printf("Usage: %s <out.atkb> <cart1.atkm> ...\\n", argvLB0RB);
        return 1;
    }

    FILE *fout = fopen(argvLB1RB, "wb");
    int cart_count = argc - 2;

    bundle_header_t hdr;
    memset(&hdr, 0, sizeof(hdr));
    hdr.magic = MAGIC_ATKB;
    hdr.version = 1;
    hdr.cartridge_count = cart_count;

    uint32_t current_offset = sizeof(bundle_header_t);

    for (int i = 0; i < cart_count; i++) {
        FILE *fc = fopen(argvLBi+2RB, "rb");
        fseek(fc, 0, SEEK_END);
        uint32_t size = ftell(fc);
        fclose(fc);

        hdr.indexLBiRB.offset = current_offset;
        hdr.indexLBiRB.size = size;
        current_offset += size;
    }

    fwrite(&hdr, sizeof(hdr), 1, fout);

    for (int i = 0; i < cart_count; i++) {
        FILE *fc = fopen(argvLBi+2RB, "rb");
        uint8_t *buf = malloc(hdr.indexLBiRB.size);
        fread(buf, 1, hdr.indexLBiRB.size, fc);
        fwrite(buf, 1, hdr.indexLBiRB.size, fout);
        free(buf);
        fclose(fc);
    }

    fclose(fout);
    return 0;
}
"""
    f.write(code.replace("LB", chr(91)).replace("RB", chr(93)))
