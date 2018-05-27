HOST=127.0.0.1
TEST_PATH=./tests
RECIPEPREFIX= # prefix char is a space, on purpose; do not delete
PHONY=clean



clean: 
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

install-deps:
	pip install -r requirements.txt

test-generate:
	pipenv install -e .
	export TEST_HOME=`pwd`; pipenv run routegen -g data/routegen_test_config.yaml > test_app.py
	unset TEST_HOME


test:	test_generate
	#PYTHONPATH=./tests
	export TEST_HOME=`pwd`
	python -m unittest discover -s snap ./tests -v
	unset TEST_HOME


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

