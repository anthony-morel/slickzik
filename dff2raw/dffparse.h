#ifndef DFFPARSE_H
#define DFFPARSE_H

struct dff_prop_s {
    uint16_t numChannels;
    uint16_t lsConfig;
    uint32_t sampleRate; 
    uint64_t dataSize;
};

void dff_set_input(FILE *f);
void dff_set_input_error_cb(void (*cb)(void *), void* context);

int dff_parse(struct dff_prop_s* props); 

#endif /* DFFPARSE_H */
