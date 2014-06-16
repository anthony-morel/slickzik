CFLAGS = -Werror
LDLIBS = -lm
.PHONY: clean install
dff2raw: dff2raw.o dffparse.o

clean:
	$(RM) *.o dff2raw

install: dff2raw
	cp -v dff2raw ~/bin
