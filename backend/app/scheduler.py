"""Optional single-worker ingestion loop. Run separately from the API."""

import logging
import time

from backend.app.ingestion import ingest

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        for source in ("usgs", "nws"):
            logging.info("%s", ingest(source))
        time.sleep(900)
