install:
	python3 setup.py sdist bdist_wheel
	pip install -e . 

clean_pyc:
	find . -type d -name __pycache__ -prune -exec rm -rf {} \; 2>/dev/null
	
clean_build:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

clean: clean_pyc clean_build

publish:
	python setup.py sdist bdist_wheel
	python3 -m twine upload --repository-url http://acc-py-repo:8081/repository/py-release-local/ -u py-service-upload -p ASK_ACC_PY_SUPPORT dist/*

test: clean_pyc
	python3 -m pytest -v --tb=line tests

.PHONY: install clean_pyc clean_build clean test publish doc