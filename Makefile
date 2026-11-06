.PHONY: prod, dev, clean

# Ensure isolated build and compiled pyc for prod
# Keep as first option so a generic make hits this
prod:
	pixi install --no-hard-links
	pixi run python -m compileall -j 20 .

# Use hardlinks etc. for dev
dev:
	pixi install

# Clear the install
clean:
	pixi clean
