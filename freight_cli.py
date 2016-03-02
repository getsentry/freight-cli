from __future__ import absolute_import, print_function

import click
import re
import requests
import sys
import json

from collections import namedtuple
from time import sleep


Task = namedtuple('Task', ['app', 'env', 'number'])


class ApiError(Exception):
    def __init__(self, code, error=None, error_name=None):
        self.code = code
        self.error = error
        self.error_name = error_name
        super(ApiError, self).__init__("{}: {}".format(self.code, self.error))


class Api(object):
    _task_id_re = re.compile(r'^([^/]+)/([^#]+)#(\d+)$')

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
        session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'freight-cli',
            'Authorization': 'Key {}'.format(self.api_key),
        })
        self._session = session
        return session

    def parse_task_id(self, task_id):
        match = self._task_id_re.match(task_id)
        if not match:
            raise ValueError('Task ID must be in format <app>/<env>#<number>')
        return Task(app=match.group(1), env=match.group(2), number=match.group(3))

    def request(self, method, path, json=None, *args, **kwargs):
        full_url = self.base_url + path

        if json:
            assert method != 'GET'
            kwargs['json'] = json
            # TODO(dcramer): flask errors out right now if we send an empty
            # JSON body
            kwargs['headers'] = {'Content-Type': 'application/json'}

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
    'auto_envvar_prefix': 'FREIGHT',
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
@click.option('--env', '-e', default=None)
@click.option('--ref', '-r', default=None)
@click.option('--force', '-f', default=False, is_flag=True)
@pass_api
def deploy(api, app, env, ref, force):
    params = {
        'app': app,
        'user': api.user,
        'force': force,
    }
    if env:
        params['env'] = env
    if ref:
        params['ref'] = ref
    data = api.post('/deploys/', params)
    print('Created new Deploy: {}'.format(data.get('name', data['id'])))


@cli.command()
@click.argument('task-id', required=True)
@pass_api
def status(api, task_id):
    task = api.parse_task_id(task_id)
    data = api.get('/deploys/{}/{}/{}/'.format(task.app, task.env, task.number))
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
@click.option('--follow', '-f', is_flag=True, default=False)
@click.option('--interval', '-i', default=0.1)
@pass_api
def tail(api, task_id, follow, interval):
    task = api.parse_task_id(task_id)
    data = api.get('/deploys/{}/{}/{}/log/?offset=-1&limit=1000'.format(
        task.app, task.env, task.number
    ))
    offset = data['nextOffset']
    if not data['text']:
        sys.stdout.write('(waiting for output..)\n')
    else:
        sys.stdout.write(data['text'])
    while True:
        data = api.get('/deploys/{}/{}/{}/log/?offset={}'.format(
            task.app, task.env, task.number, offset
        ))
        offset = data['nextOffset']
        sys.stdout.write(data['text'])
        sleep(interval)


@cli.command()
@click.argument('task-id', required=True)
@pass_api
def cancel(api, task_id):
    task = api.parse_task_id(task_id)
    data = api.put('/deploys/{}/{}/{}/'.format(
        task.app, task.env, task.number
    ), {'status': 'cancelled'})
    print('Deploy (ID = {}) was cancelled.'.format(data['id']))


@cli.group()
def app():
    pass


@app.command('list')
@pass_api
def app_list(api):
    data = api.get('/apps/')
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write('\n')


@app.command('show')
@click.argument('app', required=True)
@pass_api
def app_show(api, app):
    data = api.get('/apps/{}/'.format(app))
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write('\n')


@app.command('create')
@click.argument('name', required=True)
@click.option('--repository', prompt=True)
@click.option('--provider', default='shell', prompt=True)
@click.option('--config', default='{}', prompt=True)
@pass_api
def app_create(api, name, repository, provider, config):
    params = {
        'name': name,
        'repository': repository,
        'provider': provider,
        'provider_config': config,
    }
    api.post('/apps/', params)
    print('Created new App: {}'.format(name))


@app.command('edit')
@click.argument('app', required=True)
@pass_api
def app_edit(api, app):
    data = api.get('/apps/{}/'.format(app))
    # id isn't editable
    data.pop('id')
    rv = click.edit(json.dumps(data, indent=2)+'\n')
    if rv is None:
        return
    rv = json.loads(rv)
    params = {}
    for k, v in rv.iteritems():
        if isinstance(v, (list, dict)):
            params[k] = json.dumps(v)
        else:
            params[k] = v
    api.put('/apps/{}/'.format(app), params)
    print('App {} was updated.'.format(app))


if __name__ == '__main__':
    cli()
