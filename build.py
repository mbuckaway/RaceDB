import os
import os.path
import shutil
import zipfile
import subprocess
import re

from helptxt.compile import CompileHelp
from helptxt.version import version

# Delete any existing releases that are unofficial.
officialReleases = ['1.32.116',]
    
def build():
    CompileHelp( 'helptxt' )
    subprocess.call( ['python3', 'manage.py', 'collectstatic', '--noinput'] )

    installDir = 'RaceDB'

    zfname = os.path.join('install', 'RaceDB-Install-{}.zip'.format(version))
    zf = zipfile.ZipFile( zfname, 'w' )

    # Write all important source files to the install zip.
    suffixes = {
        'py',
        'txt', 'md',
        'html', 'css', 'js',
        'png', 'gif', 'jpg', 'ico',
        'json',
        'xls', 'xlsx',
        'gz',
        'ttf',
        'bash',
    }
    if not os.path.isdir("install"):
        os.mkdir("install")
    for root, dirs, files in os.walk('.'):
        # Skip over any src or .git files
        src = re.search("^./src.*", root)
        if src:
            print("Skipping {}".format(src.string))
            continue
        git = re.search("^./.git.*", root)
        if git:
            print("Skipping {}".format(git.string))
            continue

        for f in files:

            # Don't include local configuration in the install.
            if f in ('time_zone.py', 'DatabaseConfig.py', 'RaceDB.json', 'AllowedHosts.py', 'FixJsonImport.py'):
                print( '****************************************' )
                print( 'skipping: {}'.format(f) )
                print( '****************************************' )
                continue
            
            fname = os.path.join( root, f )
            if 'racedb' in fname.lower() and fname.lower().endswith('.json'):
                continue
            if any( d in fname for d in ['EV', 'GFRR', 'usac_heatmap', 'usac_bug', 'test_data', 'migrations_old', "bugs"] ):
                continue
            if os.path.splitext(fname)[1][1:] in suffixes:
                print( 'writing: {}'.format(fname))
                zf.write( fname, os.path.join(installDir, fname) )

    # pyllrp  is not downloaded from git, so we no longer include it here
    zf.close()
    

if __name__ == '__main__':
    build()

