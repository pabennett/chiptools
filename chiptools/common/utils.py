import subprocess
import os
import logging
import threading
import time

if __name__ == '__main__':
    import exceptions
else:
    from chiptools.common import exceptions

log = logging.getLogger(__name__)


def getDateString():
    return time.strftime('%d%m%y_%H%M%S')


def parseRange(astr):
    """
    Parse the input string numeric range and return a set of numbers.
    >>> parseRange('1-3, 5, 8, 10')
    [1, 2, 3, 5, 8, 10]
    >>> parseRange('1, 2, 3, 4, 5')
    [1, 2, 3, 4, 5]
    >>> parseRange('1-5, 9-5') # Negative ranges are ignored
    [1, 2, 3, 4, 5]
    """
    result = set()
    for part in astr.split(','):
        x = part.split('-')
        result.update(range(int(x[0]), int(x[-1])+1))
    return sorted(result)


def relativePathToAbs(path, root):
    """If the path is relative convert it into an absolute path
    >>> relativePathToAbs('../test.txt', 'c:/folder')
    'c:\\\\test.txt'
    >>> relativePathToAbs('c:/test.txt', 'c:/folder')
    'c:/test.txt'
    >>> relativePathToAbs('../../test.txt', 'c:/folder/f1/f2/')
    'c:\\\\folder\\\\test.txt'
    """
    if not os.path.isabs(path):
        return os.path.normpath(os.path.join(root, path))
    return path


def format_paths(attribute, root):
    return relativePathToAbs(
        os.path.normpath(os.path.expandvars(attribute)),
        root
    )


def time_delta_string(start_time, end_time):
    """Return a string representing the time delta in ms
    >>> time_delta_string(50e-3, 100e-3)
    '50.0ms'
    """
    return str(seconds_to_timestring(end_time-start_time))


def seconds_to_timestring(duration):
    """
    Return a formatted time-string for the given duration in seconds.
    Provides auto-rescale/formatting for values down to ns resolution
    >>> seconds_to_timestring(1.0)
    '1.0s'
    >>> seconds_to_timestring(100e-3)
    '100.0ms'
    >>> seconds_to_timestring(500e-6)
    '500.0us'
    >>> seconds_to_timestring(20000.0)
    '20000.0s'
    >>> seconds_to_timestring(453e-9)
    '453.0ns'
    >>> seconds_to_timestring(3000e-9)
    '3.0us'
    >>> seconds_to_timestring(100e-12)
    '0.1ns'
    """
    if duration >= 1000e-3:
        return str(duration) + "s"
    if duration >= 1000e-6:
        return str(duration * 1e3) + "ms"
    if duration >= 1000e-9:
        return str(duration * 1e6) + "us"
    return str(duration * 1e9) + "ns"


def execute(command, path=None, shell=True, quiet=False):
    return popen_throws_ex(command, path, quiet)


def call(command, path=None, shell=True):
    '''
    Call the executable in the given path, any messages the program generates
    will be routed to stdout and stderr.
    '''
    return_val = 0
    if path:
        return_val = subprocess.call(
            command,
            shell=shell,
            cwd=os.path.expandvars(path)
        )
    else:
        return_val = subprocess.call(command, shell=shell)
    if return_val != 0:
        raise exceptions.ExecutionError(return_val)


def popen_throws_ex(command, path=None, quiet=False):
    '''
    Call the executable in the given path, hiding standard output unless the
    return value is an error. If the return value is an error raise an
    exception for the caller to handle.
    '''

    if quiet:
        returnVal, stdout, stderr = popen_quiet(command, path)
    else:
        returnVal, stdout, stderr = popen(command, path)

    if returnVal != 0:
        errstring = ''
        if stdout:
            errstring += stdout + '\n'
        if stderr:
            errstring += str(stderr) + '\n'
        raise exceptions.ExecutionError(errstring)

    return returnVal, stdout, stderr


def tee(infile, *files):
    """
    Print `infile` to `files` in a separate thread.
    """
    def fanout(infile, *files):
        while True:
            line = infile.readline().decode('utf-8')
            if line != '':
                for f in files:
                    f.write(line.rstrip() + '\n')  # Normalise line ends
            else:
                break
        infile.close()
    t = threading.Thread(target=fanout, args=(infile,)+files)
    t.daemon = True
    t.start()
    return t


class LogWrapper:
    """Simple class to provide a file interface using a logger
    message function"""
    def __init__(self, logfn):
        self.logfn = logfn

    def write(self, line):
        """Use the logfunction to print the message, strip off any line ends"""
        self.logfn(line.rstrip())


def teed_call(cmd_args, **kwargs):
    stdout, stderr = [kwargs.pop(s, None) for s in ['stdout', 'stderr']]
    p = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE if stdout is not None else None,
        stderr=subprocess.PIPE if stderr is not None else None,
        **kwargs
    )
    threads = []
    if stdout is not None:
        threads.append(tee(p.stdout, stdout, LogWrapper(log.info)))
    if stderr is not None:
        threads.append(tee(p.stderr, stderr, LogWrapper(log.error)))
    for t in threads:
        t.join()  # wait for IO completion
    return p.wait()


def popen(command, path=None):
    from io import StringIO
    fout, ferr = StringIO(), StringIO()
    exitcode = teed_call(command, cwd=path, stdout=fout, stderr=ferr)
    stdout = fout.getvalue()
    stderr = ferr.getvalue()
    return exitcode, stdout, stderr


def popen_quiet(command, path=None):
    '''
    Call the executable in the given path and return the standard output and
    error streams.
    '''
    returnVal = 0
    stdout = ''
    stderr = ''
    if path:
        process = subprocess.Popen(
            command,
            cwd=path,
            stdout=subprocess.PIPE
        )
        # execute it, get stdout and stderr
        stdout, stderr = process.communicate()
        # when finished, get the exit code
        returnVal = process.wait()
    else:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE
        )
        # execute it, get stdout and stderr
        stdout, stderr = process.communicate()
        # when finished, get the exit code
        returnVal = process.wait()

    if stdout:
        stdout = stdout.decode('utf-8')
    if stderr:
        stderr = stderr.decode('utf-8')

    return returnVal, stdout, stderr

if __name__ == '__main__':
    import doctest
    doctest.testmod()
