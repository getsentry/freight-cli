.DELETE_ON_ERROR: venv
venv:
	python3 -m venv venv
	./venv/bin/pip install -e  .


# remove builtin magics, for sane debug (-d) output
.SUFFIXES:
export MAKEFLAGS = --no-builtin-rules --no-builtin-variables
