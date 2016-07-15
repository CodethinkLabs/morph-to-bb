#!/bin/sh

if test -e recipes; then
	rm -rf recipes
fi

if ! test -e definitions; then
	git clone --depth=1 git@ocelab.codethink.co.uk:codethink/definitions.git
fi
if ! test -e poky; then
	git clone --depth=1 git://git.yoctoproject.org/poky
fi
if ! test -e morph-to-bb; then
	git clone git@github.com:CodethinkLabs/morph-to-bb.git
fi
(
	cd definitions
	../morph-to-bb/morph-to-bb.py ../recipes systems/minimal-system-x86_32-generic.morph
#	../morph-to-bb/morph-to-bb.py ../recipes jlr/systems/ias-minimal-x86_32.morph
)

TEMPLATECONF=$PWD/recipes/meta-definitions/conf source poky/oe-init-build-env
