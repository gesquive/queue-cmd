##queue-cmd

Queue shell commands to be executed in a pool of threads

```
usage: queue-cmd [-h] [-v] [-l LOG_FILE] [-u] [-V] [-n QUEUE_NAME] [-s] [-q]
                 [-o [NUM_LINES]] [-t]
                 [command]

Queue shell commands.

Options:
  -h, --help            Show this help message and exit.
  -v, --verbose         Writes all messages to console.
  -l LOG_FILE, --log-file LOG_FILE
  -u, --update          Checks server for an update, replaces the current
                        version if there is a newer version available.
  -V, --version         show program's version number and exit

Queue Options:
  command               The shell command to run. Required when adding a
                        command.
  -n QUEUE_NAME, --queue-name QUEUE_NAME
                        The unique queue name to perform this action on.

Status Options:
  -s, --print-status    Print the status of the current queue.
  -q, --print-queue     Print the queue of commands.
  -o [NUM_LINES], --print-output [NUM_LINES]
                        Print the last NUM_LINES of the current command.
  -t, --tail-output     Tail the output of the current command.
```

#### Installation Instructions

Run the following command:
```
SDIR=/usr/local/bin/; wget https://raw.github.com/gesquive/queue-cmd/master/queue-cmd.py -O ${SDIR}/queue-cmd && chmod +x ${SDIR}/queue-cmd
```

Change the value of `SDIR` to change the destination directory.

