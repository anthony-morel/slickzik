#include <ctype.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include "dffparse.h"

char *prgname;

struct weights {
    float front;
    float centre;
    float sub;
    float rear;
};

#define NUM_CHANNELS_MAX (6)

int dsd_unpack_to_float(int numChannels, size_t dataSize, FILE *fin, FILE *fout)
{
    float sample[8 * NUM_CHANNELS_MAX];
    uint8_t ch_byte[NUM_CHANNELS_MAX];
    uint8_t mask;
    int i, j, k;

    for (i = 0; i < dataSize / numChannels; ++i) {
        if (fread(ch_byte, 1, numChannels, fin) != numChannels) {
            fprintf(stderr, "\n%s - Premature end of file\n", prgname);
            return 1;
        }
        /* Unpack 8 bits of DSD (channel byte) per channel
           into 8 interleaved floats */
        for (mask = 0x80, j = 0; mask != 0; mask >>= 1, j += numChannels) {
            for (k = 0; k < numChannels; ++k) {
                sample[j+k] = ch_byte[k] & mask ? 1. : -1.;
            }
        }
        if (fwrite(sample, sizeof(float) * 8, numChannels, fout) != numChannels) {
            fprintf(stderr, "\n%s - Write error\n", prgname);
            return 1;
        }
    }
    return 0;
}
      

int dsd_unpack_to_float_mix(int numChannels, size_t dataSize,
                            const struct weights* w, FILE *fin, FILE *fout)
{
    float sample[8 * 2]; /* 2 channel output (8 x float samples) */
    uint8_t ch_byte[NUM_CHANNELS_MAX];
    uint8_t mask;
    float mono;
    float gain;
    int i, j;

    /* 5 ch: 0-Left, 1-Right, 2-Centre, 3-Rear L, 4-Rear R
       6 ch: 0-Left, 1-Right, 2-Centre, 3-Sub, 4-Rear L, 5-Rear R */
    gain = 1./(w->front + w->centre + (numChannels==6 ? w->sub:0.) + w->rear);
    for (i = 0; i < dataSize / numChannels; ++i) {
        if (fread(ch_byte, 1, numChannels, fin) != numChannels) {
            fprintf(stderr, "\n%s - Premature end of file\n", prgname);
            return 1;
        }
        for (mask = 0x80, j = 0; mask != 0; mask >>= 1, j += 2) {
            mono = ch_byte[2] & mask ? w->centre : -w->centre;
            if (numChannels == 6) {
                mono += ch_byte[3] & mask ? w->sub : -w->sub;
            }
            sample[j] = ((ch_byte[0] & mask ? w->front : -w->front)
                         + (ch_byte[numChannels-2] & mask ? w->rear : -w->rear)
                         + mono) * gain;
            sample[j+1] = ((ch_byte[1] & mask ? w->front : -w->front)
                           + (ch_byte[numChannels-1] & mask ? w->rear : -w->rear)
                           + mono) * gain;
        }
        if (fwrite(sample, sizeof(float) * 8, 2, fout) != 2) {
            fprintf(stderr, "\n%s - Write error\n", prgname);
            return 1;
        }
    }
    return 0;
}

void usage()
{
    fprintf(stderr,
            "usage: %s [-h] [-p] [-m [-f A][-c A][-s A][-r A]] [dffile] > rawfile\n"
            "\nConvert DFF sound file to 32-bit (float) raw.\n"
            "\npositional arguments:\n"
            "  dffile  DSD audio in interchange File Format (use input pipe if absent)\n"
            "\noptional arguments:\n"
            "  -h\tshow this help message and exit\n"
            "  -p\tprint DFF header info and exit\n"
            "  -m\tmixdown 5-channel and 6-channel audio to stereo\n"
            "  -f\tfront channels attenuation A = 0,1,.. (dB) or off, to disable\n"
            "  -c\tcentre channel attenuation A = 0,1,.. (dB) or off, to disable\n"
            "  -r\trear channels attenuation  A = 0,1,.. (dB) or off, to disable\n"
            "  -s\tsubwoofer chnl attenuation A = 0,1,.. (dB) or off, to disable\n",
            prgname);
}

void error(void* context)
{
    fprintf(stderr, "\n%s - Read error\n", prgname);
    exit(1);
}

float get_weight(char* arg)
{
    float dB;

    if (isdigit(arg[0])) {
        dB = atof(arg);
        return pow(10., -dB / 20.);
    }
    else if (strncmp(arg, "off", 3) == 0) {
        return 0.;
    }
    else {
        fprintf(stderr, "\n%s - Bad attentuation value %s\n", prgname, arg);
        exit(1);
    }
}

int main(int argc, char *argv[])
{
    int opt_print = 0;
    int opt_mixdown = 0;
    FILE *fin = stdin;
    struct weights w = { 1., M_SQRT1_2, M_SQRT1_2, 1. };
    int c;
    int ret;
    struct dff_prop_s props;

    prgname = argv[0];
    opterr = 0;

    while ((c = getopt(argc, argv, "pmf:c:r:s:h")) != -1) {
        switch (c) {
            case 'p': opt_print = 1; break;
            case 'm': opt_mixdown = 1; break;
            case 'f': w.front = get_weight(optarg); break;
            case 'c': w.centre = M_SQRT1_2 * get_weight(optarg); break;
            case 'r': w.rear = get_weight(optarg); break;
            case 's': w.sub = M_SQRT1_2 * get_weight(optarg); break;
            case 'h':
                usage();
                return 0;
            case '?':
            default:
                usage();
                return 1;
        }
    }
    if (optind < argc) {
        fin = fopen(argv[optind],"rb");
        if (fin == NULL) {
            fprintf(stderr, "\n%s - Cannot open file: %s\n\n",
                    prgname, argv[optind]);
            return 1;
        }
    }

    dff_set_input(fin);
    dff_set_input_error_cb(error, NULL);
    ret = dff_parse(&props);

    if (ret != 0) {
        fprintf(stderr, "\n%s - Invalid (or unsupported) DFF file\n\n", prgname);
    }
    else if (opt_print) {
        printf("\nnumChannels     = %u\n", props.numChannels);
        printf("sampleRate      = %u Hz\n", props.sampleRate);
        printf("compressionType = Not compressed\n");
        printf("speaker config# = %u\n", props.lsConfig);
        printf("DSD data size   = %lu\n\n", props.dataSize);
        ret = 0;
    }
    else if (props.numChannels <= NUM_CHANNELS_MAX) {
        if (opt_mixdown) {
            if (props.numChannels == 5 || props.numChannels == 6) {
                ret = dsd_unpack_to_float_mix(props.numChannels, props.dataSize, &w, fin, stdout);
            }
            else {
                fprintf(stderr, "\n%s - Unsupported downmix of numChannels = %d\n\n",
                        prgname, props.numChannels);
                ret = 1;
            }
        }
        else {
            ret = dsd_unpack_to_float(props.numChannels, props.dataSize, fin, stdout);
        }        
    }
    else {
        fprintf(stderr, "\n%s - Unsupported numChannels = %d\n\n",
                prgname, props.numChannels);
        ret = 1;
    }

    return ret;
}


