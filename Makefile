.ONESHELL:
.PHONY: dependencies install clean

PREFIX=/usr/local

.DEFAULT_GOAL := dist

export PIP_REQUIRE_VIRTUALENV=true

.venv:
	python -m venv .venv

dependencies: .venv requirements.txt
	. .venv/bin/activate
	pip install -r requirements.txt

dist: .venv dependencies src
	. .venv/bin/activate
	pip install pyinstaller
	pyinstaller --add-data "data/credentials.json:data" --onefile --name=rofi-calendar src/rofi_calendar.py
	pip uninstall -y pyinstaller

install:
	cp -v dist/rofi-calendar "$(PREFIX)/bin/rofi-calendar"

clean:
	rm -vrf build
	rm -vrf dist
	rm -vrf .venv
