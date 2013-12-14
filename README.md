queue-cmd
=========

Queue shell commands to be executed in a pool of threads

```
Usage: queue-cmd.py [options] command
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
```
