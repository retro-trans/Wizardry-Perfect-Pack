"""Stage an isolated emulator copy of a verified overlay. Default dry run.

Only this project's ignored emulator profile is modified. Originals and the
user's regular RPCS3 profile are never opened for writing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from verify_build import ROOT,verify


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--write',action='store_true');p.add_argument('--update-existing',action='store_true',help='Restore original game files, then overlay this build in the existing project-local test copy');p.add_argument('--executable-only',action='store_true',help='Atomically replace EBOOT.elf only; require every other overlay file to match already. The running game uses the update after restart.');p.add_argument('--changed-files',action='store_true',help='Update differing overlay files only, after the project-local emulator closes. Preserve controllers, saves and all other assets.');args=p.parse_args()
 report=verify(args.build)
 runtime=ROOT/'work/source/rpcs3_reader'
 destination=runtime/'dev_hdd0/game/NPJB00162'
 if args.executable_only or args.changed_files:
  if not destination.is_dir():raise ValueError('No existing isolated test game')
  manifest=json.loads((args.build/'manifest.json').read_text(encoding='utf8'))
  different=[r['file'] for r in manifest['files'] if not (destination/r['file']).is_file() or hashlib.sha256((destination/r['file']).read_bytes()).hexdigest()!=r['sha256']]
  if args.executable_only and any(name!='USRDIR/EBOOT.elf' for name in different):raise ValueError('Non-executable test files differ; use --changed-files with the emulator closed')
  print(json.dumps(dict(build=str(args.build),files_to_update=different,other_overlay_files_match=True,restart_required=bool(different)),indent=2))
  if args.write and different:
   if args.changed_files:
    # Read process paths; never stop a user's emulator or discard progress.
    query="Get-Process rpcs3 -ErrorAction SilentlyContinue | ForEach-Object { try { $_.Path } catch {} }"
    running=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',query],capture_output=True,text=True,check=False)
    if running.returncode not in (0,1):raise ValueError('Could not check the test emulator; close it before updating')
    target_runtime=(runtime/'rpcs3.exe').resolve()
    if any(Path(line.strip()).resolve()==target_runtime for line in running.stdout.splitlines() if line.strip()):
     raise ValueError('Close this project\'s test emulator before applying the update. Save your progress first.')
   for name in different:
    target=destination/name;temporary=target.with_suffix(target.suffix+'.update')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(args.build/'overlay'/name,temporary)
    temporary.replace(target)
   print('Updated differing test files atomically. Restart the test game to load them; controller settings and saves were preserved.')
  elif not args.write:print('Dry run: nothing written.')
  return
 if destination.exists() and not args.update_existing:raise ValueError('Test staging already exists; pass --update-existing to refresh this project-local test copy')
 print(json.dumps(dict(build=args.build.as_posix(),destination=str(destination),files=report['manifest_files'],profile='project-local; originals untouched'),indent=2))
 if not args.write:print('Dry run: nothing written.');return
 shutil.copytree(ROOT/'work/source/NPJB00162',destination,dirs_exist_ok=args.update_existing)
 shutil.copytree(args.build/'overlay',destination,dirs_exist_ok=True)
 firmware=ROOT.parent/'Wizardry Prisoners of the Lost City/work/source/rpcs3_reader/dev_flash'
 shutil.copytree(firmware,runtime/'dev_flash',dirs_exist_ok=True)
 (runtime/'GuiConfigs').mkdir(exist_ok=True)
 (runtime/'GuiConfigs/CurrentSettings.ini').write_text('[main_window]\ninfoBoxEnabledWelcome=false\n',encoding='utf8')
 print('Staged isolated test copy. Boot USRDIR/EBOOT.elf from the printed destination.')


if __name__=='__main__':main()
