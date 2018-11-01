#!/usr/bin/env python

# depinst.py - installs the dependencies needed to test
#              a Boost library
#
# Copyright 2016 Peter Dimov
#
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt

import re
import sys
import os
import argparse

def is_module( module, gitmodules ):

    return ( 'libs/' + module ) in gitmodules

def module_for_header( header, excludedmodules, gitmodules ):

    if header in excludedmodules:

        return excludedmodules[ header ]

    else:

        # boost/function.hpp
        matches = re.match( 'boost/([^\\./]*)\\.h[a-z]*$', header )

        if matches and is_module( matches.group( 1 ), gitmodules ):

            return matches.group( 1 )

        # boost/numeric/conversion.hpp
        matches = re.match( 'boost/([^/]*/[^\\./]*)\\.h[a-z]*$', header )

        if matches and is_module( matches.group( 1 ), gitmodules ):

            return matches.group( 1 )

        # boost/numeric/conversion/header.hpp
        matches = re.match( 'boost/([^/]*/[^/]*)/', header )

        if matches and is_module( matches.group( 1 ), gitmodules ):

            return matches.group( 1 )

        # boost/function/header.hpp
        matches = re.match( 'boost/([^/]*)/', header )

        if matches and is_module( matches.group( 1 ), gitmodules ):

            return matches.group( 1 )

        print 'Cannot determine module for header', header

        return None

def scan_header_dependencies( file, excludedmodules, gitmodules, deps ):

    for line in file:

        matches = re.match( '[ \t]*#[ \t]*include[ \t]*["<](boost/[^">]*)[">]', line )

        if matches:

            header = matches.group( 1 )

            module = module_for_header( header, excludedmodules, gitmodules )

            if module:

                if not module in deps:

                    vprint( 'Adding dependency', module )
                    deps[ module ] = 0

def scan_directory( directory, excludedmodules, gitmodules, deps ):

    vprint( 'Scanning directory', directory )

    if os.name == 'nt':
        directory = unicode( directory )

    for root, dirs, files in os.walk( directory ):

        for file in files:

            fullfilename = os.path.join( root, file )

            vprint( 'Scanning file', fullfilename )

            with open( fullfilename, 'r' ) as f:

                scan_header_dependencies( f, excludedmodules, gitmodules, deps )

def scan_module_dependencies( module, excludedmodules, gitmodules, deps, dirs ):

    vprint( 'Scanning module', module )

    for dir in dirs:
        scan_directory( os.path.join( 'libs', module, dir ), excludedmodules, gitmodules, deps )

def read_exceptions():

    # exceptions.txt is the output of "boostdep --list-exceptions"

    excludedmodules = {}

    module = None

    with open( os.path.join( os.path.dirname( sys.argv[0] ), 'exceptions.txt' ), 'r' ) as f:

        for line in f:

            line = line.rstrip()

            matches = re.match( '(.*):$', line )
            
            if matches:

                module = matches.group( 1 ).replace( '~', '/' )

            else:

                header = line.lstrip()
                excludedmodules[ header ] = module

    return excludedmodules

def read_gitmodules():

    gitmodules = []

    with open( '.gitmodules', 'r' ) as f:

        for line in f:

            line = line.strip()

            matches = re.match( 'path[ \t]*=[ \t]*(.*)$', line )

            if matches:

                gitmodules.append( matches.group( 1 ) )
                
    return gitmodules

def install_modules( deps, excludedmodules, gitmodules, git_args ):

    modules = []

    for module, i in deps.items():

        if not i:

            modules += [ module ]

            deps[ module ] = 1 # mark as installed


    if len( modules ) == 0:

        return 0


    print 'Installing modules: ', ', '.join(modules)

    command = 'git submodule -q update --init ' + git_args + ' libs/' + ' libs/'.join( modules )

    #print command

    os.system( command );

    for module in modules:

        scan_module_dependencies( module, excludedmodules, gitmodules, deps, [ 'include', 'src' ] )

    return len( modules )


if( __name__ == "__main__" ):

    parser = argparse.ArgumentParser( description='Installs the dependencies needed to test a Boost library.' )

    parser.add_argument( '-v', '--verbose', help='enable verbose output', action='store_true' )
    parser.add_argument( '-I', '--include', help="additional subdirectory to scan; defaults are 'include', 'src', 'test'; can be repeated", metavar='DIR', action='append' )
    parser.add_argument( '-g', '--git_args', help="additional arguments to `git submodule update`", default='', action='store' )
    parser.add_argument( 'library', help="name of library to scan ('libs/' will be prepended)" )

    args = parser.parse_args()

    if args.verbose:

        def vprint( *args ):
            for arg in args:
                print arg,
            print

    else:

        def vprint( *args ):
            pass

    # vprint( '-I:', args.include )

    excludedmodules = read_exceptions()
    # vprint( 'Exceptions:', excludedmodules )

    gitmodules = read_gitmodules()
    # vprint( '.gitmodules:', gitmodules )

    module = args.library

    deps = { module : 1 }

    dirs = [ 'include', 'src', 'test' ]

    if args.include:
        for dir in args.include:
          dirs.append( dir )

    # vprint( 'Directories:', dirs )

    scan_module_dependencies( module, excludedmodules, gitmodules, deps, dirs )

    # vprint( 'Dependencies:', deps )

    while install_modules( deps, excludedmodules, gitmodules, args.git_args ):
        pass
