import asyncio
import base64
import datetime
from functools import wraps
import io
import mimetypes

from werkzeug import Response  # pip install Kyoukai
import dicttoxml  # pip install dicttoxml
import ujson as json  # pip install ujson


class JSONFile:
    def __init__(self, filename, loop=None):
        self.filename = filename
        loop = loop or asyncio.get_event_loop()
        loop.create_task(self._task)

    def _reload(self):
        with open(self.filename) as f:
            self.cache = json.load(f)

    async def _task(self):
        while self._run:
            self._reload()
            await asyncio.sleep(900)

    def __getitem__(self, i):
        return self.cache[i]

    def __del__(self):
        self._run = False


KEYS = JSONFile("api_keys.json")


def confirm_key(key):
    return key in KEYS


def key_is_sudo(key):
    return KEYS[key]["sudo"]


def arg_as(fmt, res, code, headers):
    if isinstance(res, io.BytesIO) and not fmt == "raw":
        res = res.read()

    if isinstance(res, str):
        if fmt == "raw" or fmt == "default":
            return Response(res, code, content_type="text/plain",
                            headers=headers)

        if fmt == "html":
            return Response(res, code, content_type="text/html",
                            headers=headers)

    elif isinstance(res, bytes):
        if fmt == "raw" or fmt == "default":
            content_type = mimetypes.guess_type("a." + headers["type"])[0]
            del headers["type"]
            return Response(res, code, content_type=content_type,
                            headers=headers)

        elif fmt == "base64":
            return Response('{"output":"'+base64.b64encode(res)+'"}', code,
                            content_type="application/json", headers=headers)

    elif isinstance(res, list) or isinstance(res, dict):
        if fmt == "json" or fmt == "default":
            return Response(json.dumps(res), code,
                            content_type="application/json", headers=headers)

        elif fmt == "xml":
            return Response(dicttoxml(res, attr_type=False), code,
                            content_type="application/xml", headers=headers)

    return Response('{"error":"Invalid format"}', 400,
                    content_type="application/json")


def multiformat(func):
    @wraps(func)
    async def inner(self, ctx, *args, **kwargs):
        url_args = ctx.request.args
        if ctx.request.path.endswith(".html"):
            url_args["format"] = "html"
        args = await func(self, ctx, *args, **kwargs)
        if isinstance(args, tuple):
            code, res, headers = args
        else:
            code, res, headers = (args.status_code, args.response[0].decode(),
                                  dict(args.headers))

        return arg_as(url_args.get("format", "default"), res, code, headers)
    return inner


def ratelimited(calls, per):
    ratelimit_cache = {}

    def decorator(func):

        @wraps(func)
        async def inner(self, ctx, *args, **kwargs):
            key = ctx.headers.get("API_KEY")  # Key-based ratelimits
            now = datetime.datetime.now()

            if key is None:
                return Response(
                    '{"error":"Unauthorized, no API_KEY header supplied"}',
                    401, content_type="application/json")

            if not confirm_key(key):
                return Response('{"error":"Invalid key"}', 403,
                                content_type="application/json")

            if key not in ratelimit_cache:
                ratelimit_cache[key] = [0, now]

            if (now - ratelimit_cache[key]).total_seconds() > per:
                ratelimit_cache[key] = [1, now]

            if ratelimit_cache[key][0] == calls:
                return Response('{"error":"Ratelimited"}', 429,
                                content_type="application/json")

            ratelimit_cache[key][0] += 1
            return await func(self, ctx, *args, **kwargs)

        return inner

    return decorator


def requires_sudo(func):
    async def inner(self, ctx, *args, **kwargs):
        key = ctx.headers["API_KEY"]
        if not key_is_sudo(key):
            return Response('{"error":"No permission, key not sudo"}', 403,
                            content_type="application/json")

        return await func(self, ctx, *args, **kwargs)
