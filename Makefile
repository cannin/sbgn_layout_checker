.PHONY: all test release current

all: test release current

test:
	./scripts/test-all.sh

release:
	$(MAKE) -C go release

current:
	$(MAKE) -C go current
