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
    print usage

def parse_chunk(defs, chunk_data):
    "Adds the chunk definition to defs if not already in"
    # Create a chunk from stratum data and merge it with the chunk file data.
    # Since I can be parsing multiple strata that may have duplicate
    # definitions of chunks, I'll need to check they're identical, and
    # warn when non-identical chunk data appears with the same name.
    # Therefore, chunks are keyed by name, not path.
    chunks = defs['chunks']
    chunk = dict(chunk_data)

    # Merge stratum's chunk spec with data from morph file
    if 'morph' in chunk_data:
        chunk_path = chunk_data['morph']
        loaded_chunk = yaml.load(file(chunk_path, 'r'))
        if loaded_chunk['kind'] != "chunk":
            print chunk_path, "is not a chunk!"
            sys.exit(1)

        if loaded_chunk['name'] != chunk['name']:
            print "Mismatched names in %s !" % chunk_path

        for key, value in loaded_chunk.iteritems():
            if key not in chunk:
                chunk[key] = value

    # Merge in defaults
    if ('build-system' in chunk 
    and chunk['build-system'] in defs['defaults']['build-systems']):
        buildsys = defs['defaults']['build-systems'][chunk['build-system']]
        for cmdname in ('configure-commands', 'build-commands', 'install-commands'):
            if (not cmdname in chunk) and (cmdname in buildsys):
                chunk[cmdname] = buildsys[cmdname]

    if chunk['name'] in chunks:
        # Possibly identical chunk
        if chunk != chunks[chunk['name']]:
            print "WARNING! Two chunks exist with the same name!"
            print "=== Old Chunk ==="
            print yaml.dump(chunks[chunk['name']])
            print "=== New Chunk ==="
            print yaml.dump(chunk)
            print "Only the old chunk will be kept"
    else:
        chunks[chunk['name']] = chunk

def add_stratum_builddepends_to_chunks(defs, stratum):
    if 'build-depends' in stratum:
        chunks = defs['chunks']
        for chunk_data in stratum['chunks']:
            chunk_name = chunk_data['name']
            if not chunk_name in chunks:
                print "Error! Chunk not found with name '%s'" % chunk_name
            chunk = chunks[chunk_name]
            if not 'stratum-build-depends' in chunk:
                chunk['stratum-build-depends'] = []
                sbdarr = chunk['stratum-build-depends']
                for stratum_bd in stratum['build-depends']:
                    sbdarr.append(stratum_bd['morph'])

def parse_stratum(defs, stratum_spec):
    "Adds the stratum definition in stratum_spec to defs if not already in"
    strata = defs['strata']
    stratum_path = stratum_spec['morph']

    if not stratum_path in strata:
        stratum = yaml.load(file(stratum_path, 'r'))
        if stratum['kind'] != "stratum":
            print stratum_path, "is not a stratum!"
            sys.exit(1)

        if 'name' in stratum_spec and stratum_spec['name'] != stratum['name']:
            print "Mismatched names in", stratum_path, "!"

        strata[stratum_path] = stratum
        for chunk_data in stratum['chunks']:
            parse_chunk(defs, chunk_data)

        add_stratum_builddepends_to_chunks(defs, stratum)

        # Strata can build-depend on strata that aren't part of the system
        if 'build-depends' in stratum:
            for bd_spec in stratum['build-depends']:
                parse_stratum(defs, bd_spec)

def parse_system(defs, system_path):
    "Adds the system definition in system_path to defs if not already in"
    if not system_path in defs['systems']:
        system = yaml.load(file(system_path, 'r'))
        if system['kind'] != "system":
            print system_path, "is not a system!"
            sys.exit(1)

        defs['systems'][system_path] = system
        for stratum_spec in system['strata']:
            parse_stratum(defs, stratum_spec)

def convert_system_to_image(recipes, system):
    image_install = []
    for stratum_spec in system['strata']:
        stratum_name = stratum_spec['name'] + "-stratum"
        image_install.append(stratum_name)

    return {'name': system['name']+"-system",
            'arch': system['arch'],
            'image_install': image_install}

def convert_stratum_to_packagegroup(defs, stratum):
    depends = []
    rdepends = []
    # Add the stratum's build-depends as DEPENDS
    if 'build-depends' in stratum:
        for stratum_spec in stratum['build-depends']:
            stratum_path = stratum_spec['morph']
            if not stratum_path in defs['strata']:
                print "Stratum %s could not be found!" % stratum_path
                sys.exit(1)
            dep_stratum = defs['strata'][stratum_path]
            depends.append("%s-stratum" % dep_stratum['name'])

    # Add the stratum's chunks as DEPENDS and RDEPENDS
    for chunk_spec in stratum['chunks']:
        depends.append("%s-chunk" % chunk_spec['name'])
        rdepends.append("%s-chunk" % chunk_spec['name'])

    return {'name': stratum['name']+"-stratum",
            'depends': depends,
            'rdepends': rdepends}

def substitute_command_variables(cmds):
    new_cmds = []
    for cmd in cmds:
        cmd = cmd.replace(r"$DESTDIR", r"${D}")
        cmd = cmd.replace(r"$PREFIX", r"${prefix}")
        new_cmds.append(cmd)

    return new_cmds

def convert_chunk_to_package(defs, chunk):
    # Chunks don't have RDEPENDS, that's handled by strata.
    strata = defs['strata']
    # Construct DEPENDS
    depends = []
    if 'build-depends' in chunk:
        for build_depend in chunk['build-depends']:
            depends.append('%s-chunk' % build_depend)
    if 'stratum-build-depends' in chunk:
        for stratum_build_depend in chunk['stratum-build-depends']:
            # stratum_build_depend is a morph path, not a name.
            if not stratum_build_depend in strata:
                print "Stratum %s could not be found!" % stratum_build_depend
                sys.exit(1)
            stratum = strata[stratum_build_depend]
            depends.append('%s-stratum' % stratum['name'])

    recipe = {'name': chunk['name']+"-chunk",
              'depends': depends}

    # construct commands
    cmdmap = {"configure-commands": "do_configure",
              "build-commands": "do_compile",
              "install-commands": "do_install"}
    for morphcmd, bbcmd in cmdmap.iteritems():
        cmds = []
        precmd = "pre-%s" % morphcmd
        postcmd = "post-%s" % morphcmd
        if precmd in chunk:
            cmds += chunk[precmd]
        if morphcmd in chunk:
            cmds += chunk[morphcmd]
        if postcmd in chunk:
            cmds += chunk[postcmd]
        if len(cmds) > 0:
            cmds = substitute_command_variables(cmds)
            recipe[bbcmd] = cmds

    return recipe

def convert_defs_to_recipes(defs, recipes):
    # This ordering is deliberate. generation of packagegroups might require
    # looking in packages, etc.
    for chunk in defs['chunks'].itervalues():
        package = convert_chunk_to_package(defs, chunk)
        recipes['packages'][package['name']] = package
    for stratum in defs['strata'].itervalues():
        packagegroup = convert_stratum_to_packagegroup(defs, stratum)
        recipes['packagegroups'][packagegroup['name']] = packagegroup
    for system in defs['systems'].itervalues():
        image = convert_system_to_image(recipes, system)
        recipes['images'][image['name']] = image

def write_image(image, images_dir):
    image_text = '''
SUMMARY = "{name}"
inherit core-image #This might need to be just "image" with more stuff set
# LICENSE = "foo" Might already be set by other classes
IMAGE_INSTALL = "{packagegroups}"
# IMAGE_ROOTFS_SIZE not sure if mandatory
    '''.format(name=image['name'],
        packagegroups=" ".join(image['image_install']))
    image_path = "%s/%s.bb" % (images_dir, image['name'])
    with open(image_path, 'w') as f:
        f.write(image_text)

def write_packagegroup(packagegroup, pg_dir):
    pg_text = '''
SUMMARY = "{name}"
PACKAGE_ARCH = "${{MACHINE_ARCH}}"
inherit packagegroup
RDEPENDS_${{PN}} = "{rdepends}"
DEPENDS_${{PN}} = "{depends}"
    '''.format(name=packagegroup['name'],
        rdepends=packagegroup['rdepends'],
        depends=packagegroup['depends'])
    pg_path = "%s/%s.bb" % (pg_dir, packagegroup['name'])
    with open (pg_path, 'w') as f:
        f.write(pg_text)

def write_package(package, packages_dir):
    package_text = '''
SUMMARY = "{name}"
DEPENDS_${{PN}} = "{depends}"
    '''.format(name=package['name'],
        depends=" ".join(package['depends']))
    package_path = "%s/%s.bb" % (packages_dir, package['name'])

    for step in ('do_configure', 'do_compile', 'do_install'):
        if step in package:
            append_text = '''
{step}() {{
\t{cmds}
}}
            '''.format(step=step, cmds="\n\t".join(package[step]))
            package_text += append_text

    with open (package_path, 'w') as f:
        f.write(package_text)

def write_recipes(recipes, recipes_dir):
    if not os.path.exists(recipes_dir):
        os.makedirs(recipes_dir)
    images_dir = "%s/images" % recipes_dir
    packagegroups_dir = "%s/packagegroups" % recipes_dir
    packages_dir = "%s/packages" % recipes_dir

    if not os.path.exists(images_dir):
        os.mkdir(images_dir)
    if not os.path.exists(packagegroups_dir):
        os.mkdir(packagegroups_dir)
    if not os.path.exists(packages_dir):
        os.mkdir(packages_dir)

    for image in recipes['images'].itervalues():
        write_image(image, images_dir)
    for packagegroup in recipes['packagegroups'].itervalues():
        write_packagegroup(packagegroup, packagegroups_dir)
    for package in recipes['packages'].itervalues():
        write_package(package, packages_dir)

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
    recipes = {'images': {}, 'packagegroups': {}, 'packages': {}}
    defs['defaults'] = yaml.load(file("DEFAULTS", 'r'))
    for system_path in argv[1:]:
        parse_system(defs, system_path)

    convert_defs_to_recipes(defs, recipes)

    write_recipes(recipes, recipes_dir)

if __name__ == "__main__":
    main(sys.argv[1:])
