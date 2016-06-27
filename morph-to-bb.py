#!/usr/bin/python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import sys

def print_usage():
    usage = '''
Usage: definitions_dir recipes_dir systems...
Where definitions_dir is a directory that contains baserock definitions,
recipes_dir is a directory that will be created and filled with bitbake recipes,
and systems... is 1 or more systems identified by name, which recipes will be
parsed from.
    '''

def main(argv):
    # Arg 1, a directory to find definitions
    # Arg 2, a directory to put recipes in
    # Arg 3..., Systems to parse

    if len(argv) < 3:
        print "Too few arguments"
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
