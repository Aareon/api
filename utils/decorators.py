import base64
import io

from werkzeug import Response  # pip install Kyoukai
import dicttoxml  # pip install dicttoxml
import ujson as json  # pip install ujson


def arg_as(fmt, res, code, kwargs):
    if isinstance(res, io.BytesIO) and not fmt == "raw":
        res = res.read()

    if isinstance(res, str):
        if fmt == "raw" or fmt == "default":
            return Response(res, code, content_type="text/plain", **kwargs)

        if fmt == "html":
            return Response(res, code, content_type="text/html", **kwargs)

    elif isinstance(res, bytes):
        if fmt == "raw" or fmt == "default":
            content_type = mimetypes.guess_type("a." + kwargs["type"])[0]
            del kwargs["type"]
            return Response(res, code, content_type=content_type, **kwargs)

        elif fmt == "base64":
            return Response('{"output":"'+base64.b64encode(res)+'"}', code,
                            content_type="application/json", **kwargs)

    elif isinstance(res, list) or isinstance(res, dict):
        if fmt == "json" or fmt == "default":
            return Response(json.dumps(res), code,
                            content_type="application/json", **kwargs)

        elif fmt == "xml":
            return Response(dicttoxml(res, attr_type=False), code,
                            content_type="application/xml", **kwargs)

    return Response('{"error":"Invalid format!"}', 400,
                    content_type="application/json")


def multiformat(func):
    async def inner(ctx, *args, **kwargs):
        url_args = ctx.request.args
        if ctx.request.path.endswith(".html"):
            url_args["format"] = "html"
        code, res, kwargs = await func(ctx, *args, **kwargs)
        return arg_as(url_args.get("format", "default"), res, code, kwargs)
    return decorator
