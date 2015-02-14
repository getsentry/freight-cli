from __future__ import absolute_import

import click
import requests


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

    delete = lambda self, url, *a, **k: \
        self.session.delete(self.base_url + '/' + url, *a, **k)
    get = lambda self, url, *a, **k: \
        self.session.get(self.base_url + '/' + url, *a, **k)
    post = lambda self, url, *a, **k: \
        self.session.post(self.base_url + '/' + url, *a, **k)
    put = lambda self, url, *a, **k: \
        self.session.put(self.base_url + '/' + url, *a, **k)


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
    api.base_url = base_url
    api.api_key = api_key
    api.user = user
    api.debug = debug


@cli.command()
@click.argument('app', required=True)
@click.argument('env', default='production')
@click.argument('ref', default='master')
@pass_api
def deploy(api, app, env, ref):
    api.post('/tasks/', {
        'app': app,
        'env': env,
        'ref': ref,
        'user': api.user
    })


if __name__ == '__main__':
    cli()
