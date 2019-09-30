HOST=127.0.0.1
TEST_PATH=./tests
RECIPEPREFIX= # prefix char is a space, on purpose; do not delete
PHONY=clean



clean: 
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name 'test_app.py' -exec rm -f {} +
	find . -name 'testbed_transforms.py' -exec rm -f {} +

install-deps:
	pipenv install
	pipenv install -e .

test-generate:	
	cp tests/testbed_transforms.py.tpl testbed_transforms.py
	export TEST_HOME=`pwd`/tests; export PYTHONPATH=`pwd`/tests; scripts/routegen -e data/good_sample_config.yaml > test_app.py

spinup:
	export TEST_HOME=`pwd`/tests; pipenv run python test_app.py --configfile data/good_sample_config.yaml

test: clean test-generate
	python -m unittest discover -s tests ./tests -v

version:
	python mark_version.py > version.py && cp version.py scripts/snap-version && chmod u+x scripts/snap-version

build-dist:
	python setup.py sdist bdist_wheel

build-testdist:
	python test_setup.py sdist bdist_wheel
	mv *.whl dist/

clean-dist:
	rm -rf dist/*
	rm -rf build/*

pypi-upload:
	twine upload -r dist/* --repository pypi

