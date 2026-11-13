"""Launch the Mac app's local web server on an OS-selected loopback port."""
import os
from pathlib import Path

data_dir = Path.home() / "Library" / "Application Support" / "Desh Ke Haath"
data_dir.mkdir(parents=True, exist_ok=True)
os.environ["DESH_DATA_DIR"] = str(data_dir)
os.environ["DESH_LOCAL_MODEL"] = "1"
os.environ["HF_HOME"] = str(data_dir / "models")

from werkzeug.serving import make_server
from app import app
import local_image

server = make_server("127.0.0.1", 0, app, threaded=True)
if os.environ.get("DESH_SKIP_MODEL_DOWNLOAD") != "1":
    local_image.start_preparation()
port_file = os.environ["DESH_PORT_FILE"]
Path(port_file).write_text(str(server.server_port), encoding="ascii")
server.serve_forever()
