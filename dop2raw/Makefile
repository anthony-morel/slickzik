CFLAGS = -Werror
LDLIBS = -lsndfile
.PHONY: clean install
dop2raw: dop2raw.o

clean:
	$(RM) *.o dop2raw

install: dop2raw
	cp -v dop2raw ~/.local/bin
