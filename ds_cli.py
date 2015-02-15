from __future__ import absolute_import, print_function

import click
import requests
import sys

from time import sleep


class ApiError(Exception):
    def __init__(self, code, error=None, error_name=None):
        self.code = code
        self.error = error
        self.error_name = error_name
        super(ApiError, self).__init__("{}: {}".format(self.code, self.error))


class Api(object):
    def __init__(self):
        self.base_url = None
        self.api_key = None
        self.user = None
        self.debug = False
        self._session = None

    @property
    def session(self):
        if self._session is not None:
            return self._session
        session = requests.Session()
        session.headers.update({'Authorization': 'Key {}'.format(self.api_key)})
        self._session = session
        return session

    def request(self, method, path, *args, **kwargs):
        full_url = self.base_url + path
        resp = getattr(self.session, method.lower())(full_url, *args, **kwargs)
        content_type = resp.headers['Content-Type']
        if content_type != 'application/json':
            raise ApiError(
                code=resp.status_code,
                error='Invalid content type: {}'.format(content_type),
            )

        data = resp.json()

        if 200 <= resp.status_code < 300:
            return data

        raise ApiError(
            code=resp.status_code,
            error=data.get('error', ''),
            error_name=data.get('error_name'),
        )

    delete = lambda s, *a, **k: s.request('DELETE', *a, **k)
    get = lambda s, *a, **k: s.request('GET', *a, **k)
    post = lambda s, *a, **k: s.request('POST', *a, **k)
    put = lambda s, *a, **k: s.request('PUT', *a, **k)


pass_api = click.make_pass_decorator(Api, ensure=True)


@click.group(context_settings={
    'auto_envvar_prefix': 'DS',
})
@click.option('--api-key', required=True)
@click.option('--base-url', required=True)
@click.option('--user', required=True)
@click.option('--debug/--no-debug', default=False)
@pass_api
def cli(api, base_url, api_key, user, debug):
    api.base_url = base_url.rstrip('/')
    api.api_key = api_key
    api.user = user
    api.debug = debug


@cli.command()
@click.argument('app', required=True)
@click.option('--env', default='production')
@click.option('--ref', default='master')
@click.option('--force', default=False)
@pass_api
def deploy(api, app, env, ref, force):
    data = api.post('/tasks/', {
        'app': app,
        'env': env,
        'ref': ref,
        'user': api.user,
        'force': force,
    })
    print('Created new Task with ID = {}'.format(data['id']))


@cli.command()
@click.argument('task-id', required=True)
@pass_api
def status(api, task_id):
    data = api.get('/tasks/{}/'.format(task_id))
    row = '{:12} {:25}'
    print('[{app}/{env} #{number}]'.format(
        app=data['app']['name'],
        number=data['number'],
        env=data['environment'],
        id=data['id']
    ))
    print(row.format('Status:', data['status']))
    print(row.format('Created:', data['dateCreated']))
    if data['status'] in ('finished', 'failed'):
        print(row.format('Started:', data['dateStarted']))
        print(row.format('Finished:', data['dateFinished']))


@cli.command()
@click.argument('task-id', required=True)
@pass_api
def tail(api, task_id):
    data = api.get('/tasks/{}/log/?offset=-1&limit=1000'.format(task_id))
    offset = data['nextOffset']
    sys.stdout.write(data['text'])
    while True:
        data = api.get('/tasks/{}/log/?offset={}'.format(task_id, offset))
        offset = data['nextOffset']
        sys.stdout.write(data['text'])
        sleep(0.5)


if __name__ == '__main__':
    cli()
