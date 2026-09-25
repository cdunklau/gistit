GistIt
######

Create Gists_ from the command line.

Supports Python 3.10+. Requires the Requests_ library.

.. _Gists: https://gist.github.com/
.. _Requests: https://requests.readthedocs.io/


Features
========

-   Public/Private Gists.
-   Easy token creation, scoped only for Gist (not the rest of GitHub)
-   Filenames with path context (optional).

Usage
=====

General usage::

    usage: gistit.py [-h] [--token TOKEN] {create,token} ...

    positional arguments:
      {create,token}        Available commands
        create              Create new gist
        token               Create a new gist access token and store it in a file

    options:
      -h, --help            show this help message and exit
      --token TOKEN, -t TOKEN
                            Path to token file

Create command::

    usage: gistit.py create [-h] [--description DESCRIPTION] [--public]
                            [--no-contextual]
                            file [file ...]

    positional arguments:
      file                  File to upload

    options:
      -h, --help            show this help message and exit
      --description DESCRIPTION, -d DESCRIPTION
                            Gist description
      --public, -p          Create as public gist
      --no-contextual, -C   Use normal filenames, without path context

Token command::

    usage: gistit.py token [-h] username

    positional arguments:
      username    Github username or email

    options:
      -h, --help  show this help message and exit
