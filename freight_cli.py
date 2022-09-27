import json
import re
import sys
from collections import namedtuple
from time import sleep
from urllib.parse import urlsplit

import click
from urllib3.connectionpool import connection_from_url

Task = namedtuple("Task", ["app", "env", "number"])


class ApiError(Exception):
    def __init__(self, code, error=None, error_name=None):
        self.code = code
        self.error = error
        self.error_name = error_name
        super().__init__(f"{self.code}: {self.error}")


class Api(object):
    _task_id_re = re.compile(r"^([^/]+)/([^#]+)#(\d+)$")

    def __init__(self):
        self.base_url = None
        self.path = None
        self.api_key = None
        self.user = None
        self.debug = False
        self._session = None

    @property
    def session(self):
        if self._session is not None:
            return self._session
        session = connection_from_url(self.base_url)
        if session.scheme == "https":
            import certifi

            session.ca_certs = certifi.where()
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "freight-cli",
                "Authorization": f"Key {self.api_key}",
            }
        )
        self._session = session
        return session

    def parse_task_id(self, task_id):
        match = self._task_id_re.match(task_id)
        if not match:
            raise ValueError("Task ID must be in format <app>/<env>#<number>")
        return Task(app=match.group(1), env=match.group(2), number=match.group(3))

    def request(self, method, path, body=None, *args, **kwargs):
        full_path = self.path + path

        method = method.upper()
        if body:
            assert method != "GET"
            kwargs["body"] = json.dumps(body)
            # TODO(dcramer): flask errors out right now if we send an empty
            # JSON body
            kwargs["headers"] = {
                **self.session.headers,
                **{"Content-Type": "application/json"},
            }

        resp = self.session.urlopen(method, full_path, *args, **kwargs)

        content_type = resp.headers["Content-Type"]
        if content_type != "application/json":
            raise ApiError(
                code=resp.status, error=f"Invalid content type: {content_type}"
            )

        data = json.loads(resp.data)

        if 200 <= resp.status < 300:
            return data

        raise ApiError(
            code=resp.status,
            error=data.get("error", ""),
            error_name=data.get("error_name"),
        )

    def delete(self, *a, **kw):
        return self.request("DELETE", *a, **kw)

    def get(self, *a, **kw):
        return self.request("GET", *a, **kw)

    def post(self, *a, **kw):
        return self.request("POST", *a, **kw)

    def put(self, *a, **kw):
        return self.request("PUT", *a, **kw)


pass_api = click.make_pass_decorator(Api, ensure=True)


@click.group(context_settings={"auto_envvar_prefix": "FREIGHT"})
@click.option("--api-key", required=True)
@click.option("--base-url", required=True)
@click.option("--user", required=True)
@click.option("--debug/--no-debug", default=False)
@pass_api
def cli(api, base_url, api_key, user, debug):
    path = urlsplit(base_url)
    api.base_url = "{}://{}".format(*path[:2])
    api.path = path[2].rstrip("/")
    api.api_key = api_key
    api.user = user
    api.debug = debug


@cli.command()
@click.argument("app", required=True)
@click.option("--env", "-e", default=None)
@click.option("--ref", "-r", default=None)
@click.option("--force", "-f", default=False, is_flag=True)
@pass_api
def deploy(api, app, env, ref, force):
    params = {"app": app, "user": api.user, "force": force}
    if env:
        params["env"] = env
    if ref:
        params["ref"] = ref
    data = api.post("/deploys/", params)
    click.echo(f'Created new Deploy: {data.get("name", data["id"])}')


@cli.command()
@click.argument("task-id", required=True)
@pass_api
def status(api, task_id):
    task = api.parse_task_id(task_id)
    data = api.get(f"/deploys/{task.app}/{task.env}/{task.number}/")
    row = "{:12} {:25}"
    click.echo(
        "[{app}/{env} #{number}]".format(
            app=data["app"]["name"],
            number=data["number"],
            env=data["environment"],
            id=data["id"],
        )
    )
    click.echo(row.format("Status:", data["status"]))
    click.echo(row.format("Created:", data["dateCreated"]))
    if data["status"] in ("finished", "failed"):
        click.echo(row.format("Started:", data["dateStarted"]))
        click.echo(row.format("Finished:", data["dateFinished"]))


@cli.command()
@click.argument("task-id", required=True)
@click.option("--follow", "-f", is_flag=True, default=False)
@click.option("--interval", "-i", default=0.1)
@pass_api
def tail(api, task_id, follow, interval):
    task = api.parse_task_id(task_id)
    data = api.get(
        f"/deploys/{task.app}/{task.env}/{task.number}/log/?offset=-1&limit=1000"
    )
    offset = data["nextOffset"]
    if not data["chunks"]:
        sys.stdout.write("(waiting for output..)\n")
    else:
        for chunk in data["chunks"]:
            sys.stdout.write(chunk["text"])
    while True:
        data = api.get(
            f"/deploys/{task.app}/{task.env}/{task.number}/log/?offset={offset}"
        )
        offset = data["nextOffset"]
        for chunk in data["chunks"]:
            sys.stdout.write(chunk["text"])
        sleep(interval)


@cli.command()
@click.argument("task-id", required=True)
@pass_api
def cancel(api, task_id):
    task = api.parse_task_id(task_id)
    data = api.put(
        f"/deploys/{task.app}/{task.env}/{task.number}/", {"status": "cancelled"}
    )
    click.echo(f'Deploy (ID = {data["id"]}) was cancelled.')


@cli.group()
def app():
    pass


@app.command("list")
@pass_api
def app_list(api):
    data = api.get("/apps/")
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


@app.command("show")
@click.argument("app", required=True)
@pass_api
def app_show(api, app):
    data = api.get(f"/apps/{app}/")
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


@app.command("create")
@click.argument("name", required=True)
@click.option("--repository", prompt=True)
@click.option("--provider", default="shell", prompt=True)
@click.option("--config", default="{}", prompt=True)
@pass_api
def app_create(api, name, repository, provider, config):
    params = {
        "name": name,
        "repository": repository,
        "provider": provider,
        "provider_config": config,
    }
    api.post("/apps/", params)
    click.echo(f"Created new App: {name}")


@app.command("edit")
@click.argument("app", required=True)
@pass_api
def app_edit(api, app):
    data = api.get(f"/apps/{app}/")
    # id isn't editable
    data.pop("id")
    rv = click.edit(json.dumps(data, indent=2) + "\n", extension=".json")
    if rv is None:
        return
    rv = json.loads(rv)
    params = {}
    for k, v in rv.items():
        if isinstance(v, (list, dict)):
            params[k] = json.dumps(v)
        else:
            params[k] = v
    api.put(f"/apps/{app}/", params)
    click.echo(f"App {app} was updated.")


@app.command("delete")
@click.argument("app", required=True)
@pass_api
def app_delete(api, app):
    click.confirm(f"Are you sure you want to delete '{app}'?", abort=True)
    data = api.delete(f"/apps/{app}/")
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


@cli.group()
def webhook():
    pass


@webhook.command("create")
@click.option("--hook", default="github", prompt=True)
@click.option("--action", default="deploy", prompt=True)
@click.option("--app", prompt=True)
@click.option("--env", prompt=True)
@pass_api
def webhook_create(api, hook, action, app, env):
    import hmac
    from hashlib import sha256

    key = f"{hook}/{action}/{app}/{env}"
    base_url = "{}://{}".format(*urlsplit(api.base_url)[:2])
    digest = hmac.new(
        api.api_key.encode("utf8"), key.encode("utf8"), sha256
    ).hexdigest()
    click.echo(f"{base_url}/webhooks/{key}/{digest}/")


if __name__ == "__main__":
    cli()
