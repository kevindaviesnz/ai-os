#include <stdio.h>
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
    } index[8];
} bundle_header_t;

int main(int argc, char **argv) {
    if (argc < 3 || argc > 10) {
        printf("Usage: %s <out.atkb> <cart1.atkm> ...\n", argv[0]);
        return 1;
    }

    FILE *fout = fopen(argv[1], "wb");
    int cart_count = argc - 2;

    bundle_header_t hdr;
    memset(&hdr, 0, sizeof(hdr));
    hdr.magic = MAGIC_ATKB;
    hdr.version = 1;
    hdr.cartridge_count = cart_count;

    uint32_t current_offset = sizeof(bundle_header_t);

    for (int i = 0; i < cart_count; i++) {
        FILE *fc = fopen(argv[i+2], "rb");
        fseek(fc, 0, SEEK_END);
        uint32_t size = ftell(fc);
        fclose(fc);

        hdr.index[i].offset = current_offset;
        hdr.index[i].size = size;
        current_offset += size;
    }

    fwrite(&hdr, sizeof(hdr), 1, fout);

    for (int i = 0; i < cart_count; i++) {
        FILE *fc = fopen(argv[i+2], "rb");
        uint8_t *buf = malloc(hdr.index[i].size);
        fread(buf, 1, hdr.index[i].size, fc);
        fwrite(buf, 1, hdr.index[i].size, fout);
        free(buf);
        fclose(fc);
    }

    fclose(fout);
    return 0;
}
