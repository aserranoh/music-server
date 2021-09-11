
'''Utilities to daemonize a process.'''

__author__ = 'Antonio Serrano Hernandez'
__copyright__ = 'Copyright 2021'
__license__ = 'proprietary'
__version__ = '0.1'
__maintainer__ = 'Antonio Serrano Hernandez'
__email__ = 'toni.serranoh@gmail.com'
__status__ = 'Development'

def _daemonize():
    '''Daemonize the current process.'''
    # Clear file creation mask
    os.umask(0)

    # Become a session leader to lose controlling TTY
    if os.fork() != 0:
        # parent
        sys.exit(0)

    # Ensure future opens won't allocate controlling TTYs
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    if os.fork() != 0:
        # parent
        sys.exit(0)

    # Change the current working directory to the root so we won't
    # prevent file systems from being unmounted
    os.chdir('/')

    # Close all open file descriptors
    for i in range(1024):
        try:
            os.close(i)
        except OSError:
            pass

    # Attach file descriptors 0, 1 and 2 to /dev/null
    os.open('/dev/null', os.O_RDWR)
    os.dup(0)
    os.dup(0)

class Daemon:
    '''A daemon process.

    The daemon is implemented with a context manager. When the context manager
    is entered, the daemon is created (process detached from controlling
    terminal, term signal managed and pidfile created. At exit, the pidfile is
    removed to inform the service manager that this service is finished.

    Example of use:

    d = Daemon(app, True, '/var/run/myapp.pid')
    with d:
        # Do stuff with app
        app.run()
    '''

    def __init__(self, app, daemonize=True, pidfile=None):
        '''Create the daemon.

        * daemonize: if True, daemonize this process.
        * pidfile: if given, the name of the file that will contain the PID of
            the daemonized process.
        '''
        self._app = app
        self._do_daemonize = daemonize
        self._pidfile = pidfile

    def __enter__(self):
        '''Enter the daemon.

        The process is daemonized.
        '''
        # Daemonize the process, if demanded
        if self._do_daemonize:
            _daemonize()

        # Write the pidfile
        if self._pidfile is not None:
            with open(self._pidfile, 'w') as file_:
                file_.write(f'{os.getpid()}')

        # Set the term signal
        signal.signal(signal.SIGINT, self._term)
        signal.signal(signal.SIGTERM, self._term)

        return self

    def _term(self, *args):
        '''TERM signal received.

        Signal the app that it must stop.
        '''
        # Stop the application
        self._app.stop()

    def __exit__(self, exc_type, exc_value, traceback):
        '''Stop this daemon.'''
        # Remove the pid file
        if self._pidfile is not None:
            try:
                os.unlink(self._pidfile)
            except OSError:
                logging.warning('cannot remove pidfile %s', self._pidfile)

