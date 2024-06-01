.PHONY: install clean

dff2raw/dff2raw:
	$(MAKE) -C dff2raw

~/.local/bin/slickzik: artwork.py metautils.py flac.py cue.py sacd.py slickzik
	python install.py $^ > $@
	chmod a+x $@

install: dff2raw/dff2raw ~/.local/bin/slickzik
	cp -v dff2raw/dff2raw ~/.local/bin

clean:
	$(MAKE) -C dff2raw $@
	$(RM) *.py~ *~

