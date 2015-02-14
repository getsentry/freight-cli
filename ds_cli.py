from __future__ import absolute_import, unicode_literals

import click
import requests


import os
import click


class Api(object):
    def __init__(self, base_url, api_key, user, debug=False):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user = user
        self.debug = debug
        self.session = self.build_session()

    def build_session(self):
        session = requests.Session()
        session.headers.update({'Authorization': 'Key {}'.format(self.api_key)})
        return session

    delete = lambda s, url, *a, **k: s.session.delete(s.base_url + '/' + url, *a, **k)
    get = lambda s, url, *a, **k: s.session.get(s.base_url + '/' + url, *a, **k)
    post = lambda s, url, *a, **k: s.session.post(s.base_url + '/' + url, *a, **k)
    put = lambda s, url, *a, **k: s.session.put(s.base_url + '/' + url, *a, **k)

pass_api = click.make_pass_decorator(Api)


@click.group()
@click.option('--api-key', required=True, envvar='DS_API_KEY')
@click.option('--base-url', required=True, envvar='DS_BASE_URL')
@click.option('--user', required=True, envvar='DS_USER')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, base_url, api_key, user, debug):
    ctx.obj = Api(base_url, api_key, user, debug)


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
