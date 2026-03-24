#include <stdio.h>
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
    uint8_t  signature[64];
} cartridge_header_t;

int main(int argc, char **argv) {
    if (argc != 5) {
        printf("Usage: %s <in.bin> <out.atkm> <module_id> <stack_size>\n", argv[0]);
        return 1;
    }

    FILE *fin = fopen(argv[1], "rb");
    FILE *fout = fopen(argv[2], "wb");
    uint32_t mod_id = atoi(argv[3]);
    uint32_t stack_size = atoi(argv[4]);

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
