ifeq ($(OS), Windows_NT)
	DOXYFILE = DoxyfileWin
else
	DOXYFILE = Doxyfile
endif

all: docs

docs: build_mkdocs build_doxygen

build_mkdocs:
	mkdocs build

build_doxygen:
	cd docs && doxygen $(DOXYFILE)

clean:
	rm -r build/site

