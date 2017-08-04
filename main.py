import importlib
import os

from kyoukai import Kyoukai

app = Kyoukai(">Terminal_ API")

for cog in os.listdir("cogs"):
    if not cog.endswith(".py"):
        continue

    lib = importlib.import_path(f"cogs.{cog}")
    lib.setup(app)

app.run("0.0.0.0", 8001)
