#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "dffparse.h"

#define TOKEN4(a,b,c,d) (((((uint32_t)(a)<<8)+(b)<<8)+(c)<<8)+(d))

#define TOKEN_FRM8 TOKEN4('F','R','M','8')
#define TOKEN_DSD  TOKEN4('D','S','D',' ')
#define TOKEN_FVER TOKEN4('F','V','E','R')
#define TOKEN_PROP TOKEN4('P','R','O','P')
#define TOKEN_SND  TOKEN4('S','N','D',' ')
#define TOKEN_FS   TOKEN4('F','S',' ',' ')
#define TOKEN_CHNL TOKEN4('C','H','N','L')
#define TOKEN_CMPR TOKEN4('C','M','P','R')
#define TOKEN_LSCO TOKEN4('L','S','C','O')
#define TOKEN_DSD  TOKEN4('D','S','D',' ')

struct ckHeader {
    uint32_t ckID;
    uint64_t ckDataSize;
};

static FILE *fin;
static void (*cb)(void *);
static void *cb_context;

void dff_set_input(FILE *f)
{
    fin = f;
}

void dff_set_input_error_cb(void (*_cb)(void *), void* context)
{
    cb = _cb;
    cb_context = context;
}

static uint32_t token4(uint8_t* b)
{
    return TOKEN4(b[0],b[1],b[2],b[3]);
}

static uint64_t token8(uint8_t* b)
{
    return ((((((((uint64_t)b[0]<<8)+b[1]<<8)+b[2]<<8)+b[3]<<8)+b[4]<<8)+b[5]<<8)+b[6]<<8)+b[7];
}

static void error()
{
    if (cb != NULL) {
        (*cb)(cb_context);
    }
    exit(1);
}

static void next_chunk(struct ckHeader* header)
{
    uint8_t buf[12];

    if (fread(buf, sizeof(buf), 1, fin) != 1) {
      error();
    }

    header->ckID = token4(buf);
    header->ckDataSize = token8(&buf[4]);
}

static uint32_t next_token4()
{
    uint8_t buf[4];

    if (fread(buf, sizeof(buf), 1, fin) != 1) {
      error();
    }

    return token4(buf);
}

static uint32_t next_token2()
{
    uint8_t buf[2];

    if (fread(buf, sizeof(buf), 1, fin) != 1) {
      error();
    }

    return (buf[0] << 8) + buf[1];
}

// fseek does not work on stdin
// TODO: expect small seek, this could be optimised for long seek 
void myseek(FILE *stream, uint64_t offset)
{
    uint8_t buf[1];
    uint64_t i;

    for (i=0; i<offset; ++i) {
        if (fread(buf, sizeof(buf), 1, fin) != 1) {
            error();
        }
    }
}


int dff_parse(struct dff_prop_s* props)
{
    struct ckHeader header;

    next_chunk(&header);

    if (header.ckID != TOKEN_FRM8)
        return 1;
    if (next_token4() != TOKEN_DSD)
        return 1;

    next_chunk(&header);

    if (header.ckID != TOKEN_FVER && header.ckDataSize != 4)
        return 1;
    if (next_token4() != TOKEN4(1,5,0,0))
        return 1;

    next_chunk(&header);

    if (header.ckID != TOKEN_PROP)
        return 1;
    if (next_token4() != TOKEN_SND)
        return 1;

    for (;;) {
        next_chunk(&header);
        switch (header.ckID) {
            case TOKEN_FS:
                if (header.ckDataSize != 4)
                    return 1;
                props->sampleRate = next_token4();
                break;
            case TOKEN_CHNL:
                if (header.ckDataSize < 2)
                    return 1;
                props->numChannels = next_token2();
                myseek(fin, header.ckDataSize - 2);
                break;
            case TOKEN_CMPR:
                if (header.ckDataSize < 4)
                    return 1;
                if (next_token4() != TOKEN_DSD)
                    return 1;
                // Not compressed
                myseek(fin, header.ckDataSize - 4);
                break;
            case TOKEN_LSCO:
                if (header.ckDataSize != 2)
                    return 1;
                props->lsConfig = next_token2();
                break;
            case TOKEN_DSD:
                props->dataSize = header.ckDataSize;
                return 0;
            default:
                //fprintf(stderr, "Found %x %lu\n", header.ckID, header.ckDataSize);
                myseek(fin, header.ckDataSize);
        }
    }
    return 0;
}

#if 0
int main()
{
    struct dff_prop_s props;

    dff_set_input(stdin);
    dff_parse(&props);

    return 0;
}
#endif
