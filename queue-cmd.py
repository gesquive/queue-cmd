#!/usr/bin/env python
# queue-cmd.py
# GusE 2013.12.16 V0.1
"""
Queue shell commands
"""
__version__ = "1.0"

import getopt
import sys
import os
import subprocess
import traceback
import logging
import logging.handlers
import tempfile

__app__ = os.path.basename(__file__)
__author__ = "Gus E"
__copyright__ = "Copyright 2013"
__credits__ = ["Gus E"]
__license__ = "GPL"
__maintainer__ = "Gus E"
__email__ = "gesquive@gmail"
__status__ = "Production"

script_www = 'https://github.com/gesquive/queue-cmd'
script_url = 'https://raw.github.com/gesquive/queue-cmd/master/queue-cmd.py'

#--------------------------------------
# Configurable Constants
LOG_FILE = '/var/log/' + os.path.splitext(__app__)[0] + '.log'
LOG_SIZE = 1024*1024*200

verbose = False
debug = False

logger = logging.getLogger(__app__)

def usage():
    usage = \
"""Usage: %s [options] command
    Queue shell commands
Options and arguments:
  command                           The shell command to run.
  -t --threads <number>             The number of threads that will run
                                        commands. (default: 1)
  -n --queue-name <name>            The unique queue name to start/add.
  -l --log-file <path>              The log file path.
  -u --update                       Checks server for an update, replaces
                                        the current version if there is a
                                        newer version available.
  -h --help                         Prints this message.
  -v --verbose                      Writes all messages to console.

    v%s
""" % (__app__, __version__)

    print usage


def main():
    global verbose, debug

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvudt:n:l:", \
        ["help", "verbose", "update", "debug",
        "threads=", "queue-name=", "log-file="])
    except getopt.GetoptError, err:
        print str(err)
        print usage()
        sys.exit(2)

    verbose = False
    debug = False
    command = None
    threads = 1
    queue_name = "default"
    log_file = LOG_FILE

    # Save forced arg
    if len(args) > 0:
        command = args[0]
    elif len(args) > 1:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            # Print out help and exit
            usage()
            sys.exit()
        elif o in ("-d", "--debug"):
            debug = True
        elif o in ("-v", "--verbose"):
            verbose = True
        elif o in ("-u", "--update"):
            update(script_url)
            sys.exit(0)
        elif o in ("-t", "--threads"):
            if not a.isdigit():
                print "threads: \'%s\' must be an integer." % a
                sys.exit(2)
            a = int(a)
            if a < 1:
                print "threads: \'%s\' must be an valid value." % a
                sys.exit(2)
            threads = a
        elif o in ("-n", "--queue-name"):
            queue_name = a
        elif o in ("-l", "--log-file"):
            log_file = a

    if not os.access(os.path.dirname(log_file), os.W_OK):
        # Couldn't write to the given log file, try writing a temporary one instead
        log_file = os.path.join(tempfile.gettempdir(),
            os.path.splitext(__app__)[0] + '.log')
        if not os.access(os.path.dirname(log_file), os.W_OK):
            print "ERROR: Cannot write to '%(log_file)s'.\nExiting." % locals()
            sys.exit(2)
    file_handler = logging.handlers.RotatingFileHandler(log_file,
                                            maxBytes=LOG_SIZE, backupCount=9)
    file_formater = logging.Formatter('%(asctime)s,%(levelname)s,%(process)d,%(message)s')
    file_handler.setFormatter(file_formater)
    logger.addHandler(file_handler)

    if verbose:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter("[%(asctime)s] %(levelname)-5.5s: %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode activated.")
    else:
        logger.setLevel(logging.INFO)

    try:
        # First check to see if we are the master or slave
        is_master = get_lock_file()

        if is_master:
            logger.info("Run in mode: master")
            daemonize()
        else:
            logger.info("Run in mode: slave")

        push_command(command)

        # Single mode just means that we can print our output to stdout
        single_mode = (threads == 1)

        shell_runners = []
        complete = 0
        while is_master:
            # Then we are the main thread, start running the threads
            cmd = get_next_command(queue_name)
            if not cmd: # Then there are no commands left to run, finish up
                logger.info("All shell commands completed.")
                break
            runner = ShellRunner(cmd, print_to_stdout=single_mode)
            shell_runners.append(runner)
            runner.start()

            # Always add on one thread to account for the Main Thread
            while (threading.activeCount() >= (threads + 1)):
                sleep(0.25)
            # One of the threads finished, cleanup
            complete += 1
            for runner in shell_runners:
                if not runner.isAlive():
                    logger.info("Shell command completed: '%s'" % runner.cmd)
                    runner.handled = True
            shell_runners = [r for r in shell_runners if not r.handled]
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception, e:
        print traceback.format_exc()

    close_lock_file()


import fcntl
import os
pid_file = None
def get_lock_file():
    global pid_file
    # Generate path
    pid_file_path = os.path.join(tempfile.gettempdir(), \
            os.path.splitext(__app__)[0])
    logger.debug("Getting lock file '%(pid_file_path)s'" % locals())
    # If the file exists, read it
    pid_file = open(pid_file_path, 'a+')
    try:
        fcntl.flock(pid_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # Another running process has this lock
        pid_file.close()
        pid_file = None
        return False

    # If the pid does not exist, replace pid with our own, run as master
    pid_file.seek(0)
    pid_file.truncate()
    pid_file.write(str(os.getpid()))
    pid_file.flush()

    return True


def close_lock_file():
    global pid_file
    if pid_file:
        pid_file.close()
    pid_file = None


def push_command(cmd, name="default"):
    logger.debug("Pushing command %(name)s:>'%(cmd)s'" % locals())
    queue_file = get_queue_file(name)
    # logger.debug("Writing too %s:%d" % (queue_file.name, queue_file.tell()))
    queue_file.write(cmd)
    queue_file.write("\n")
    queue_file.flush()
    queue_file.close()


def get_next_command(name="default"):
    logger.debug("Getting command for %(name)s" % locals())
    queue_file = get_queue_file(name)
    queue_file.seek(0)
    commands = queue_file.readlines()
    cmd = None
    if len(commands) > 0:
        queue_file.seek(0)
        queue_file.truncate()
        cmd = commands[0].strip()
    if len(commands) > 1:
        for line in commands[1:]:
            queue_file.write(line)
    queue_file.close()
    logger.debug("Got next command %(name)s:>'%(cmd)s'" % locals())
    return cmd


import fcntl
from time import sleep
def get_queue_file(name="default"):
    queue_file_path = os.path.join(tempfile.gettempdir(), \
            os.path.splitext(__app__)[0] + "-" + name + ".q")
    logger.debug("Acquiring queue file lock for '%(queue_file_path)s'" % locals())
    lock_aquired = False
    while not lock_aquired:
        queue_file = open(queue_file_path, "a+")
        try:
            fcntl.flock(queue_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_aquired = True
            return queue_file
        except IOError:
            # Another running process has this lock, wait for it to give it up
            sleep(.5)
    logger.debug("Queue lock file acquired")


def pid_exists(pid):
    """
    Returns true if pid is still running
    """
    return os.path.exists('/proc/%d' % pid)


import threading
import subprocess
class ShellRunner(threading.Thread):
    cmd = None
    cwd = None
    seperate = True
    stdout = subprocess.PIPE

    print_to_stdout = False
    cmd_output = []

    def __init__(self, cmd, cwd=None, seperate=True, stdout=subprocess.PIPE,
        print_to_stdout=False):

        threading.Thread.__init__(self)
        self.cmd = cmd
        self.cwd = cwd
        self.seperate = seperate
        self.stdout = stdout
        self.print_to_stdout = print_to_stdout
        if print_to_stdout:
            self.stdout = None

    def run(self):
        proc = subprocess.Popen(self.cmd, shell=self.seperate,
            stdout=self.stdout, stderr=subprocess.STDOUT, cwd=self.cwd)
        if not self.print_to_stdout:
            for line in iter(proc.stdout.readline, ""):
                cmd_output.append(line)
            proc.wait()
        else:
            logger.debug("Running '%s' as pid=%d", self.cmd, proc.pid)
            proc.wait()


import sys
import os
def daemonize (stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    '''This forks the current process into a daemon.
    The stdin, stdout, and stderr arguments are file names that
    will be opened and be used to replace the standard file descriptors
    in sys.stdin, sys.stdout, and sys.stderr.
    These arguments are optional and default to /dev/null.
    Note that stderr is opened unbuffered, so
    if it shares a file with stdout then interleaved output
    may not appear in the order that you expect.
    '''
    # Do first fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0) # Exit first parent.
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)

    # Decouple from parent environment.
    os.chdir("/")
    os.umask(0)
    os.setsid()

    # Do second fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0) # Exit second parent.
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)

    # Now I am a daemon!

    # Redirect standard file descriptors.
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def update(dl_url, force_update=False):
    """
Attempts to download the update url in order to find if an update is needed.
If an update is needed, the current script is backed up and the update is
saved in its place.
"""
    import urllib
    import re
    from subprocess import call
    def compare_versions(vA, vB):
        """
Compares two version number strings
@param vA: first version string to compare
@param vB: second version string to compare
@author <a href="http_stream://sebthom.de/136-comparing-version-numbers-in-jython-pytho/">Sebastian Thomschke</a>
@return negative if vA < vB, zero if vA == vB, positive if vA > vB.
"""
        if vA == vB: return 0

        def num(s):
            if s.isdigit(): return int(s)
            return s

        seqA = map(num, re.findall('\d+|\w+', vA.replace('-SNAPSHOT', '')))
        seqB = map(num, re.findall('\d+|\w+', vB.replace('-SNAPSHOT', '')))

        # this is to ensure that 1.0 == 1.0.0 in cmp(..)
        lenA, lenB = len(seqA), len(seqB)
        for i in range(lenA, lenB): seqA += (0,)
        for i in range(lenB, lenA): seqB += (0,)

        rc = cmp(seqA, seqB)

        if rc == 0:
            if vA.endswith('-SNAPSHOT'): return -1
            if vB.endswith('-SNAPSHOT'): return 1
        return rc

    # dl the first 256 bytes and parse it for version number
    try:
        http_stream = urllib.urlopen(dl_url)
        update_file = http_stream.read(256)
        http_stream.close()
    except IOError, (errno, strerror):
        print "Unable to retrieve version data"
        print "Error %s: %s" % (errno, strerror)
        return

    match_regex = re.search(r'__version__ *= *"(\S+)"', update_file)
    if not match_regex:
        print "No version info could be found"
        return
    update_version = match_regex.group(1)

    if not update_version:
        print "Unable to parse version data"
        return

    if force_update:
        print "Forcing update, downloading version %s..." \
            % update_version
    else:
        cmp_result = compare_versions(__version__, update_version)
        if cmp_result < 0:
            print "Newer version %s available, downloading..." % update_version
        elif cmp_result > 0:
            print "Local version %s newer then available %s, not updating." \
                % (__version__, update_version)
            return
        else:
            print "You already have the latest version."
            return

    # dl, backup, and save the updated script
    app_path = os.path.realpath(sys.argv[0])

    if not os.access(app_path, os.W_OK):
        print "Cannot update -- unable to write to %s" % app_path

    dl_path = app_path + ".new"
    backup_path = app_path + ".old"
    try:
        dl_file = open(dl_path, 'w')
        http_stream = urllib.urlopen(dl_url)
        total_size = None
        bytes_so_far = 0
        chunk_size = 8192
        try:
            total_size = int(http_stream.info().getheader('Content-Length').strip())
        except:
            # The header is improper or missing Content-Length, just download
            dl_file.write(http_stream.read())

        while total_size:
            chunk = http_stream.read(chunk_size)
            dl_file.write(chunk)
            bytes_so_far += len(chunk)

            if not chunk:
                break

            percent = float(bytes_so_far) / total_size
            percent = round(percent*100, 2)
            sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" %
                (bytes_so_far, total_size, percent))

            if bytes_so_far >= total_size:
                sys.stdout.write('\n')

        http_stream.close()
        dl_file.close()
    except IOError, (errno, strerror):
        print "Download failed"
        print "Error %s: %s" % (errno, strerror)
        return

    try:
        os.rename(app_path, backup_path)
    except OSError, (errno, strerror):
        print "Unable to rename %s to %s: (%d) %s" \
            % (app_path, backup_path, errno, strerror)
        return

    try:
        os.rename(dl_path, app_path)
    except OSError, (errno, strerror):
        print "Unable to rename %s to %s: (%d) %s" \
            % (dl_path, app_path, errno, strerror)
        return

    try:
        import shutil
        shutil.copymode(backup_path, app_path)
    except:
        os.chmod(app_path, 0755)

    print "New version installed as %s" % app_path
    print "(previous version backed up to %s)" % (backup_path)
    return




if __name__ == '__main__':
    main()
