.PHONY: build, clean

build:
	pixi install --no-hard-links
	python -m compileall -j 20

clean:
	pixi clean
