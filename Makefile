# Jupiter distribution build entry points. Run `make help` for the list.
include distro.conf

PYTHON ?= python3

.PHONY: help art rpms iso all test test-installer test-config clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

art: ## Regenerate the placeholder splash PNG (replace the file with real art later)
	$(PYTHON) scripts/generate-placeholders.py

rpms: ## Build jupiter-branding and jupiter-installer RPMs into build/repo
	scripts/build-iso.sh rpms

iso: ## Build the live ISO (also builds the RPMs first)
	scripts/build-iso.sh all

all: iso ## Alias for iso

test: test-installer test-config ## Run all tests that do not need Fedora

test-installer: ## Run installer unit and TUI tests (needs textual and pytest)
	cd installer && PYTHONPATH=. $(PYTHON) -m pytest -q

test-config: ## Validate branding, kickstart and package configuration
	$(PYTHON) -m pytest -q tests

clean: ## Remove build outputs
	rm -rf build installer/build installer/*.egg-info
