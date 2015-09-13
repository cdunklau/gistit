#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import io
import json
import pprint
import argparse
import getpass
import uuid

import requests



def create_command(args):
    file_paths = args.file_paths
    description = args.description
    public = args.public
    if args.anonymous:
        token = None
    else:
        with open(args.token) as f:
            token = json.load(f)['token']
        
    client = GithubAPIClient(token)
    try:
        gist_url = client.new_gist(
            file_paths, description=description, public=public)
        print(gist_url)
        return 0
    except GithubAPIException as e:
        github_api_exception_to_stderr('Failed to create gist', e)
        return 1


def token_command(args):
    username = args.username
    password = getpass.getpass('Password for {0}: '.format(username))
    token_file = args.token

    client = GithubAPIClient()
    try:
        result = client.new_gist_token(username, password)
        token_id, token, fingerprint = result
    except GithubAPIException as e:
        github_api_exception_to_stderr('Failed to create new token', e)
        return 1

    print('Saving token to {0}'.format(token_file), file=sys.stderr)
    obj = {
        'token_id': token_id,
        'token': token,
        'fingerprint': fingerprint,
    }
    with open(token_file, 'w') as f:
        json.dump(obj, f)


class GithubAPIException(Exception):
    def __init__(self, message, context):
        self.message = message
        self.context = context


def github_api_exception_to_stderr(message, exc):
    print(message, file=sys.stderr)
    print(exc.message, file=sys.stderr)
    pprint.pprint(exc.data, stream=sys.stderr)


class GithubAPIClient(object):
    def __init__(self, token=None):
        session = requests.Session()
        session.headers['content-type'] = 'application/json'
        session.headers['accept'] = 'application/vnd.github.v3+json'
        if token:
            session.headers['authorization'] = 'token ' + token
        self._session = session

    def _url(self, path):
        return 'https://api.github.com/' + path.lstrip('/')

    def new_gist(self, file_paths, description=u'', public=False):
        """
        Create a new gist with files from the filesystem and return
        the URL to the newly created gist.
        """
        payload = {
            u'description': description,
            u'public': public,
            u'files': {}
        }
        for path in file_paths:
            with io.open(path, encoding='utf-8') as f:
                file_contents = f.read()
            filename = os.path.basename(path)
            payload[u'files'][filename] = {u'content': file_contents}

        response = self._session.post(
            self._url('/gists'), data=json.dumps(payload))

        self._expect_created(response, 'Failed to create new gist')

        info = response.json()

        return info['html_url']

    def new_gist_token(self, username, password):
        """
        Create a new authorization token for gist and return
        the token's ID, the token itself, and the fingerprint.
        """
        fingerprint = str(uuid.uuid4())
        payload = {
            u'scopes': ['gist'],
            u'note': u'Created by gistit.py',
            u'fingerprint': fingerprint,
        }
        response = self._session.post(
            self._url('/authorizations'),
            data=json.dumps(payload), auth=(username, password))

        self._expect_created(response, 'Failed to create authorization token')

        info = response.json()
        token_id = info['id']
        token = info['token']
        fingerprint = info['fingerprint']

        return token_id, token, fingerprint

    def _expect_created(self, response, message):
        if response.status_code != 201:
            raise GithubAPIException(message, response.json())


def make_parser():
    default_token_file = os.path.expanduser('~/.gistit_token')

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--token', '-t', default=default_token_file,
        help='Path to token file')
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    create_parser = subparsers.add_parser('create', help='Create new gist')
    create_parser.add_argument(
        '--description', '-d', default=u'', help='Gist description')
    create_parser.add_argument(
        '--public', '-p', action='store_true', help='Create as public gist')
    create_parser.add_argument(
        '--anonymous', '-a', action='store_true', help='Create as anonymous')
    create_parser.add_argument(
        'file_paths', metavar='file', nargs='+', help='File to upload')
    create_parser.set_defaults(func=create_command)

    token_parser = subparsers.add_parser(
        'token', help='Create a new gist access token and store it in a file')
    token_parser.add_argument('username', help='Github username or email')
    token_parser.set_defaults(func=token_command)

    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()
    command = args.func
    sys.exit(command(args))


if __name__ == '__main__':
    main()
