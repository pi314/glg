import argparse
import sys
import threading
import pathlib
import logging

from signal import SIGINT, SIGTERM, SIGKILL

from . import iroiro

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


logger = logging.getLogger('glg')

plock = threading.Lock()
proc = None


class GitFileMonitor(FileSystemEventHandler):
    def __init__(self, callback, interested=set()):
        self.callback = callback
        self.interested = interested

    def on_any_event(self, event):
        if event.is_directory:
            return

        if hasattr(event, 'dest_path') and event.dest_path:
            path = pathlib.Path(event.dest_path)
        else:
            path = pathlib.Path(event.src_path)

        if self.interested and path.name not in self.interested:
            return
        logger.debug(f'{event.event_type} [{path}]')
        self.callback()


def git_log_thread_main():
    global pager_proc

    while True:
        # retrieve git log
        git_lg_proc = iroiro.run(['git', '--no-pager', 'lg', '--color=always'], stdin=None, stdout=True, stderr=True)
        if git_lg_proc.stderr:
            for line in git_lg_proc.stderr:
                print(line, file=sys.stderr)
        if git_lg_proc.returncode:
            break
        git_log = git_lg_proc.stdout.lines

        # display git log with pager
        with plock:
            pager_proc = iroiro.command(['less', '-R', '+g'], stdin=git_log, stdout=None, stderr=None)

        try:
            pager_proc.run(wait=False)
            logger.info(f'pager pid = {pager_proc.proc.pid}')
            pager_proc.wait()
        except Exception as e:
            logger.error(str(e))
            break

        logger.info(f'ret = {pager_proc.returncode}')

        if pager_proc.signaled == SIGTERM:
            with plock:
                pager_proc = None
            continue

        if pager_proc.returncode == 0:
            continue

        pager_proc = None
        break


def refresh_git_log():
    logger.info('refresh_git_log')
    with plock:
        try:
            pager_proc.kill(SIGTERM)
        except:
            pass
    logger.info('refresh_git_log end')


def main():
    parser = argparse.ArgumentParser(prog='glg',
            description='git lg that automatically refresh')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug log')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(filename='glg.log')
        fh.setFormatter(logging.Formatter(fmt='[%(asctime)s][%(levelname)s] %(message)s'))
        logger.addHandler(fh)

    p = iroiro.run('git rev-parse --show-toplevel'.split())
    if p.stderr:
        for line in p.stderr:
            print(line, file=sys.stderr)
    if p.returncode:
        sys.exit(p.returncode)
    repo_root = pathlib.Path(p.stdout.lines[0])

    def errorout(lines):
        kwargs = {'file': sys.stderr}
        print('Error:', **kwargs)
        for line in lines:
            print(line, **kwargs)
        sys.exit(1)

    dot_git = repo_root / '.git'
    if dot_git.is_dir():
        head_dir = dot_git

    elif dot_git.is_file():
        # maybe it's a worktree
        with dot_git.open() as f:
            lines = [line.strip() for line in f]
            if len(lines) != 1:
                error([
                    dot_git,
                    'File is not a valid .git worktree',
                    ])
                sys.exit(1)

        line = lines[0]
        if not line.startswith('gitdir: '):
            errorout([
                'File: ' + str(dot_git),
                line,
                'File is not a valid .git worktree',
                ])

        gitdir = pathlib.Path(line[len('gitdir: '):])
        if not gitdir.exists():
            errorout([gitdir, 'Not exists'])
        if not gitdir.is_dir():
            errorout([gitdir, 'Not dir'])

        commondir = gitdir / 'commondir'
        if not commondir.exists():
            errorout([commondir, 'Not exists'])

        with commondir.open() as f:
            lines = [line.strip() for line in f]
            if len(lines) != 1:
                errorout([commondir, 'File is not a valid .git worktree commondir file'])
                sys.exit(1)
            rpath = lines[0]

        commondir = (gitdir / rpath).resolve()

        if not commondir.exists():
            errorout([commondir, 'Not exists'])

        dot_git = commondir
        head_dir = gitdir

    else:
        errorout(dot_git)

    dot_git_refs = dot_git / 'refs'

    looker1 = GitFileMonitor(refresh_git_log, interested='HEAD')
    looker2 = GitFileMonitor(refresh_git_log)

    git_head_observer = Observer()
    git_head_observer.schedule(looker1, head_dir)
    git_head_observer.schedule(looker2, dot_git_refs, recursive=True)
    git_head_observer.start()

    t = threading.Thread(target=git_log_thread_main)
    t.daemon = True
    t.start()

    try:
        t.join()
    except KeyboardInterrupt:
        pass

    logger.info('bye')


if __name__ == '__main__':
    main()
