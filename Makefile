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

test:	
	PYTHONPATH=./tests python -m unittest discover -t . ./tests -v

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

