.PHONY: build test clean
build:
	gcc -O2 -o bin/app src/main.c
test:
	./bin/app --self-test
clean:
	rm -f bin/app
