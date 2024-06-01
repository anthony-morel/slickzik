/* vim: set ts=4 sw=4 et :
 *
 * This program tests whether a (libsndfile-supported) audio file contains DSD
 * over PCM.  If stdio is redirected to a file then it proceeds with extraction
 * into a raw format at 1 float/sample/channel and (multiple of) 2.8224 MHz
 * sampling.
 *
 * DSD over PCM (or DoP) is documented here:
 * https://dsd-guide.com/sites/default/files/white-papers/DoP_openStandard_1v1.pdf
 */

#include <sndfile.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>

#define NUM_CHANNELS_MAX (6)

static SNDFILE* sf;
static SF_INFO sf_info;
static bool test_only;

static inline sf_count_t dop_to_pcm(void)
{
    /* 24-bit samples shall alternate 0x05---- / 0xfa----
     * libsndfile returns 32-bits samples 0x05----00 / 0xfa----00
     */
    int dop[NUM_CHANNELS_MAX];
    float out[16 * NUM_CHANNELS_MAX];
    uint8_t mask[NUM_CHANNELS_MAX] = { 0 };

    sf_count_t i = 0;
    for ( ; i < sf_info.frames; i++) {
        if (sf_readf_int(sf, dop, 1) != 1)
            break;

        for (int ch = 0; ch < sf_info.channels; ch++) {
            uint8_t marker = dop[ch] >> 24;
            if (!mask[ch] && (marker == 0x05 || marker == 0xfa)) {
                mask[ch] = marker;
            } else if (marker == (uint8_t)~mask[ch]) {
                mask[ch] = marker;
            } else {
                return i;
            }
            dop[ch] >>= 8;  /* align the 16 DSD bits with LSB */
        }
        if (test_only) continue;

        /* Unpack 16 bits of DSD per channel into 16 channel-interleaved floats
         */
        for (unsigned mask = 0x8000, j = 0; mask != 0;
                mask >>= 1, j += sf_info.channels) {
            for (unsigned k = 0; k < sf_info.channels; k++) {
                out[j+k] = dop[k] & mask ? 1.f : -1.f;
            }
        }
        if (fwrite(out, sizeof(float[16]), sf_info.channels, stdout) != sf_info.channels) {
            fprintf(stderr, "Write error... aborting...\n");
            return i;
        }
    }
    return i;
}

int main(int argc, char *argv[])
{
    if (argc <= 1) {
        fprintf(stderr, "Usage: dop2dsd DSD_over_PCM.file [> out.dsd]\n");
        return EXIT_FAILURE;
    }
    const char *fname = argv[1];

    sf = sf_open(fname, SFM_READ, &sf_info);
    if (!sf) {
        fprintf(stderr, "%s: %s\n", fname, sf_strerror(NULL));
        return EXIT_FAILURE;
    }

    /* Input must have 24 bit samples and be a multiple of 176.4 kHz
     * sampling (single-rate DSD, aka DSD64) */
    unsigned bytes = sf_info.format & SF_FORMAT_SUBMASK;
    int dsd_rate = sf_info.samplerate / 176400;
    if (sf_info.channels <= 0 || sf_info.channels > NUM_CHANNELS_MAX ||
            bytes != 3 || dsd_rate <= 0 ||
            dsd_rate * 176400 != sf_info.samplerate) {
        fprintf(stderr, "%s: cannot extract %d-ch DSD over PCM "
                "at %d-byte/sample and %d Hz\n",
                fname, sf_info.channels, bytes, sf_info.samplerate);
        return EXIT_FAILURE;
    }

    test_only = isatty(fileno(stdout));
    if (test_only) {
        printf("%s: testing for %d-ch DSD%d\n", fname, sf_info.channels, 64 * dsd_rate);
    }

    sf_count_t count = dop_to_pcm();

    if (test_only) {
        printf("%s:%ld:%s\n", fname, count, count != sf_info.frames ? "ERROR" : "OK");
    }
    return count != sf_info.frames ? EXIT_FAILURE : EXIT_SUCCESS;
}
