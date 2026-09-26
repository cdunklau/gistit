#!/usr/bin/env python3
import sys
import os
import json
import pprint
import argparse
import getpass
import uuid

import requests


def create_command(args):
    file_paths = [os.path.abspath(p) for p in args.file_paths]
    try:
        paths_gist_filenames = _generate_gist_filenames(file_paths, args.contextual)
    except DuplicateFilenames as e:
        print(str(e), file=sys.stderr)
        print("Use contextual behavior (default) to avoid this", file=sys.stderr)
        sys.exit(1)
    description = args.description
    public = args.public
    with open(args.token, encoding="utf-8") as f:
        token = f.readline().strip()

    client = GithubAPIClient(token)
    try:
        gist_url = client.new_gist(
            paths_gist_filenames, description=description, public=public
        )
        print(gist_url)
        return 0
    except GithubAPIException as e:
        github_api_exception_to_stderr("Failed to create gist", e)
        return 1


def make_parser():
    default_token_file = os.path.expanduser("~/.gistit_token")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--token", "-t", default=default_token_file, help="Path to token file"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    create_parser = subparsers.add_parser("create", help="Create new gist")
    create_parser.add_argument(
        "--description", "-d", default="", help="Gist description"
    )
    create_parser.add_argument(
        "--public", "-p", action="store_true", help="Create as public gist"
    )
    create_parser.add_argument(
        "--no-contextual",
        "-C",
        action="store_false",
        dest="contextual",
        help="Use normal filenames, without path context",
    )
    create_parser.add_argument(
        "file_paths", metavar="file", nargs="+", help="File to upload"
    )
    create_parser.set_defaults(func=create_command)

    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        parser.exit(2)
    command = args.func
    sys.exit(command(args))


class DuplicateFilenames(Exception):
    def __init__(self, filename, path1, path2):
        self.filename = filename
        self.path1 = path1
        self.path2 = path2

    def __str__(self):
        return (
            f"Duplicate filename {self.filename} for paths "
            f"{self.path1} and {self.path2}"
        )


def _generate_gist_filenames(absolute_paths, contextual=True):
    """
    Return a list of (file_path, gist_file_name) tuples. The
    ``gist_file_name`` is contextual based on the path component
    common to all of the files, unless ``contextual`` is false, then
    ``gist_file_name`` is merely the basename.

    :param file_paths:  Sequence of absolute paths to files.
    """
    if not contextual:
        paths_gist_filenames = []
        filenames_to_paths = {}
        for path in absolute_paths:
            filename = os.path.basename(path)
            if filename in filenames_to_paths:
                raise DuplicateFilenames(filename, filenames_to_paths[filename], path)
            filenames_to_paths[filename] = path
            paths_gist_filenames.append((path, os.path.basename(path)))
        return paths_gist_filenames
    prefix = _real_commonprefix(absolute_paths)
    paths_gist_filenames = []
    for path in absolute_paths:
        gist_filename = "-".join(os.path.relpath(path, prefix).split(os.sep))
        paths_gist_filenames.append((path, gist_filename))
    return paths_gist_filenames


def _real_commonprefix(absolute_paths):
    """
    ``os.path.commonprefix`` might return invalid paths, so we verify
    the result ends with os.sep.
    """
    assert len(absolute_paths)
    assert all(os.path.isabs(p) for p in absolute_paths)
    if len(absolute_paths) == 1:
        return os.path.dirname(absolute_paths[0]) + os.sep
    candidate_prefix = os.path.commonprefix(absolute_paths)
    if candidate_prefix.endswith(os.sep):
        return candidate_prefix
    else:
        return candidate_prefix.rpartition(os.sep)[0] + os.sep


class GithubAPIException(Exception):
    def __init__(self, message, context):
        self.message = message
        self.context = context


def github_api_exception_to_stderr(message, exc):
    print(message, file=sys.stderr)
    print(exc.message, file=sys.stderr)
    pprint.pprint(exc.context, stream=sys.stderr)


class GithubAPIClient(object):
    def __init__(self, token):
        session = requests.Session()
        session.headers["content-type"] = "application/json"
        session.headers["accept"] = "application/vnd.github+json"
        session.headers["x-github-api-version"] = "2026-03-10"
        session.headers["authorization"] = "token " + token
        self._session = session

    def _url(self, path):
        return "https://api.github.com/" + path.lstrip("/")

    def new_gist(self, paths_gist_filenames, description="", public=False):
        """
        Create a new gist with files from the filesystem and return
        the URL to the newly created gist.
        """
        payload = {"description": description, "public": public, "files": {}}
        for path, gist_filename in paths_gist_filenames:
            with open(path, encoding="utf-8") as f:
                file_contents = f.read()
            print(path, gist_filename)
            payload["files"][gist_filename] = {"content": file_contents}

        response = self._session.post(self._url("/gists"), data=json.dumps(payload))

        self._expect_created(response, "Failed to create new gist")

        info = response.json()

        return info["html_url"]

    def _expect_created(self, response, message):
        if response.status_code != 201:
            raise GithubAPIException(message, response.json())


if __name__ == "__main__":
    main()


import unittest
import subprocess


class PathGenerationTestCase(unittest.TestCase):
    def test_single_yields_only_filename(self):
        path = "/foo/bar.py"
        result = _generate_gist_filenames([path])
        self.assertEqual(result, [(path, os.path.basename(path))])

    def test_basic(self):
        path1 = "/foo/sub1/spam"
        path2 = "/foo/sub2/eggs"
        fname1 = "sub1-spam"
        fname2 = "sub2-eggs"
        result = _generate_gist_filenames(["/foo/sub1/spam", "/foo/sub2/eggs"])
        expected = [(path1, fname1), (path2, fname2)]
        self.assertEqual(result, expected)

    def test_not_contextual(self):
        path1 = "/foo/sub1/spam"
        path2 = "/foo/sub2/eggs"
        fname1 = "spam"
        fname2 = "eggs"
        result = _generate_gist_filenames(
            ["/foo/sub1/spam", "/foo/sub2/eggs"], contextual=False
        )
        expected = [(path1, fname1), (path2, fname2)]
        self.assertEqual(result, expected)

    def test_not_contextual_errors_on_duplicate_filenames(self):
        with self.assertRaises(DuplicateFilenames) as ctx:
            _generate_gist_filenames(
                ["/foo/sub1/file", "/foo/sub2/file"], contextual=False
            )
        e = ctx.exception
        self.assertEqual(e.filename, "file")
        self.assertEqual(e.path1, "/foo/sub1/file")
        self.assertEqual(e.path2, "/foo/sub2/file")

    def test__real_commonprefix_single(self):
        result = _real_commonprefix(["/foo/bar/baz"])
        self.assertEqual(result, "/foo/bar/")

    def test__real_commonprefix_basic(self):
        result = _real_commonprefix(["/foo/bar", "/foo/baz"])
        self.assertEqual(result, "/foo/")

    def test__real_commonprefix_different_depth(self):
        result = _real_commonprefix(["/foo/bar/spam", "/foo/eggs"])
        self.assertEqual(result, "/foo/")

    def test__real_commonprefix_nocommon_returns_root(self):
        result = _real_commonprefix(["/foo/bar", "/spam/eggs"])
        self.assertEqual(result, "/")


class ArgParserTestCase(unittest.TestCase):
    def test_create_parser_no_contextual(self):
        args = make_parser().parse_args(["create", "--no-contextual", "somefile"])
        self.assertTrue(args.contextual == False)

    def test_create_parser_contextual(self):
        args = make_parser().parse_args(["create", "somefile"])
        self.assertTrue(args.contextual == True)


class UsageTestCase(unittest.TestCase):
    def run_gistit(self, args, **kwargs):
        kwargs.setdefault("check", True)
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("encoding", "utf-8")
        cmd_args = [sys.executable, "gistit.py", *args]
        return subprocess.run(cmd_args, **kwargs)

    def assert_readme_contains_help_output(self, help_output):
        with open("README.rst", encoding="utf-8") as f:
            readme = f.read()

        help_lines = [line.rstrip() for line in help_output.splitlines()]
        indented_help_lines = []
        for line in help_lines:
            indented_line = "    " + line if line else ""
            indented_help_lines.append(indented_line)
        indented_help_output = "\n".join(indented_help_lines) + "\n"
        self.assertIn(indented_help_output, readme)

    def test_general_usage_in_readme(self):
        help_output = self.run_gistit(["-h"]).stdout
        self.assert_readme_contains_help_output(help_output)

    def test_create_usage_in_readme(self):
        help_output = self.run_gistit(["create", "-h"]).stdout
        self.assert_readme_contains_help_output(help_output)


class SimpleRun(unittest.TestCase):
    def setUp(self):
        cmd_args = [sys.executable, 'gistit.py', '--help']
        self.help_output_lines = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE).communicate()[0].decode('utf-8').splitlines()[0]

    def test_no_args(self):
        cmd_args = [sys.executable, 'gistit.py']
        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        test_stdout, test_stderr = proc.communicate()
        # using `stdout`/`stderr` because in `python2` the default help is raised
        # by the parser, and it is written to `stderr`, while in `python3` we
        # are using the parser to print help explicitly and it being written to stdout
        test_output_line = ''
        if test_stdout:
            test_output_line = test_stdout.decode('utf-8').splitlines()[0]
        else:
            test_output_line = test_stderr.decode('utf-8').splitlines()[0]
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(test_output_line, self.help_output_lines)

