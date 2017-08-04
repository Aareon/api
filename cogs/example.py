from kyoukai.routegroup import RouteGroup, route
from werkzeug import Response

from utils import decorators


class Example(RouteGroup, prefix="/debug"):
    @route("/")
    @decorators.multiformat
    async def debug_root(self, ctx):
        # In case of multiformat:
        # return in format (response, status_code, kwargs_for_response)
        # returning a Response works too, but is significantly slower
        return ("This is a debug route", 200, {})

    @route("/sudo")
    @decorators.requires_sudo
    async def debug_sudo(self, ctx):
        # Not multiformat, so just a werkzeug.Response
        return Response("This is a sudo route", 200)

    @route("/ratelimited")
    @decorators.ratelimited(5, 60)  # 5 requests every minute
    async def debug_ratelimited(self, ctx):
        return Response("This endpoint has ratelimits", 200)

    @route("/mixed")
    @decorators.requires_sudo
    @decorators.ratelimited(10, 10)
    @decorators.multiform  # always last
    async def debug_mixed(self, ctx):
        return ("This route has all decorators in the correct order", 200, {})


def setup(app):
    app.root.add_route_group()
