#!/usr/bin/python

import sys

def main(argv):
    # Arg 1, a directory to find definitions
    # Arg 2, a directory to put recipes in
    # Arg 3..., Systems to parse
    print "Arg 1 is", argv[0]
    print "Arg 2 is", argv[1]
    print "Other args are", argv[2:]

if __name__ == "__main__":
    main(sys.argv[1:])
