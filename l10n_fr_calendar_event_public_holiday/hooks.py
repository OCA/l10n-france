# copyright David BEAL @ Akretion

import csv
import logging
from pathlib import Path

from odoo.modules.module import get_module_path

logger = logging.getLogger(__name__)

MODULE = __name__[12 : __name__.index(".", 13)]


def post_init_hook(env):
    """Import French public holidays from CSV file after module installation."""
    path = Path(get_module_path(MODULE)) / "data/feries.csv"
    with open(path) as file:
        data = csv.reader(file, delimiter=";")
        header = next(data)
        lines = list(data)
        res = env["calendar.event"].load(header, lines)
        if res.get("messages"):
            for msg in res["messages"]:
                logger.info(f"Fail on row {msg['record']}: {msg['message']}")
        else:
            logger.info(f"Successful Import ! Created IDs : {res['ids']}")
