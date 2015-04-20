# freight-cli

This is a command line interface to [Freight](https://github.com/getsentry/freight).

```bash
$ freight --api-key <api_key> --base-url http://<host>:<port>/api/0/ --user username@domainname.com deploy example
Created new Task with ID = 1

$ freight --api-key <api_key> --base-url http://<host>:<port>/api/0/ --user username@domainname.com tail -f 1
(waiting for output..)
# ...
```
