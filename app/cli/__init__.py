"""FastSoyAdmin CLI — 业务模块代码生成工具。"""

import click

from app.cli.commands.gen import gen
from app.cli.commands.init import init
from app.cli.commands.initdb import initdb


@click.group()
def cli():
    """FastSoyAdmin 业务模块代码生成器"""


cli.add_command(init)
cli.add_command(gen)
cli.add_command(initdb)
