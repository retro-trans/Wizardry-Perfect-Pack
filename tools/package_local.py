"""Package a verified local overlay and test instructions. Default dry run.

This is a local testing bundle, not a release or a source patch distributor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from verify_build import ROOT, verify


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--write',action='store_true')
    args=p.parse_args()
    report=verify(args.build)
    version=report['version']
    output=ROOT/'work/output'/('Wizardry_Perfect_Pack_Prisoners_EN_'+version+'_local-overlay.zip')
    files=sorted(p for p in args.build.rglob('*') if p.is_file())
    print(json.dumps(dict(version=version,files=len(files),bytes=sum(p.stat().st_size for p in files),output=str(output)),indent=2))
    instructions=('LOCAL TEST OVERLAY '+version+'\n\n'
        'Target: NPJB00162, Prisoners of the Lost City from the Japanese Perfect Pack.\n'
        'English draft; see manifest for acceptance work and review flags.\n'
        'Copy the overlay contents into a separate copy of your extracted NPJB00162 game.\n'
        'Boot USRDIR/EBOOT.elf in RPCS3; EBOOT.BIN remains the original executable.\n'
        'Keep your original game files and saves separately.\n'
        'This does not patch NPJB00163 / Labyrinth of Lost Souls.\n'
        'This is not a signed PS3 package or a rebuilt install ISO.\n'
        'No public release has been created.\n')
    print(instructions)
    if not args.write:
        print('Dry run: nothing written.');return
    if output.exists():raise ValueError('Bundle already exists; use a new build version')
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in files:
            archive.write(path,path.relative_to(args.build).as_posix())
        archive.writestr('README.txt',instructions)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('Bundle CRC verification failed')
    hasher=hashlib.sha256()
    with output.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
    digest=hasher.hexdigest()
    output.with_suffix('.sha256').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    print('Created and CRC-verified local bundle:',output,'SHA256:',digest)


if __name__=='__main__':main()
