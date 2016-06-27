#!/usr/bin/python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import os, sys, yaml

def print_usage():
    usage = '''
Usage: recipes_dir systems...
Where recipes_dir is a directory that will be created and filled with bitbake
recipes, and systems... is 1 or more systems identified by file path, which
recipes will be parsed from.
Run this script from the root of the definitions directory.
    '''

def parse_stratum(defs, stratum_spec):
    "Adds the stratum definition in stratum_spec.morph if not already in"
    strata = defs['strata']
    stratum_path = stratum_spec['morph']

    if not stratum_path in strata:
        stratum = yaml.load(file(stratum_path, 'r'))
        if stratum_spec['name'] != stratum['name']:
            print "Mismatched names in", stratum_spec['morph'], "!"
        strata[stratum_path] = stratum


def parse_system(defs, system_path):
    "Adds the system definition in system_path to defs if not already in"
    if not system_path in defs['systems']:
        system = yaml.load(file(system_path, 'r'))
        defs['systems'][system_path] = system
        for stratum_spec in system['strata']:
            parse_stratum(defs, stratum_spec)

def main(argv):
    # Arg 1, a directory to put recipes in
    # Arg 2..., Systems to parse

    if len(argv) < 2:
        print "Too few arguments"
        print_usage()
        sys.exit(1)

    if not os.path.isfile("DEFAULTS"):
        print "DEFAULTS file not found. Is this being run from the top of definitions?"
        sys.exit(1)

    recipes_dir = argv[0]
    defs = {'systems': {}, 'strata': {}, 'chunks': {}}
    for system_path in argv[1:]:
        parse_system(defs, system_path)

    print yaml.dump(defs)

if __name__ == "__main__":
    main(sys.argv[1:])
