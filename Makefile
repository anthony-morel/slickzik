.PHONY: all install clean

all: dff2raw/dff2raw dop2raw/dop2raw

dff2raw/dff2raw:
	$(MAKE) -C $(@D)

dop2raw/dop2raw:
	$(MAKE) -C $(@D)

~/.local/bin/slickzik: artwork.py metautils.py flac.py cue.py sacd.py slickzik
	python install.py $^ > $@
	chmod a+x $@

install: ~/.local/bin/slickzik dff2raw/dff2raw dop2raw/dop2raw
	cp -v dff2raw/dff2raw dop2raw/dop2raw ~/.local/bin

clean:
	$(MAKE) -C dff2raw $@
	$(MAKE) -C dop2raw $@
	$(RM) *.py~ *~

