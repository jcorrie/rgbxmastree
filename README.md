# rgbxmastree

Code examples for the RGB Xmas Tree.

This repo is based on the code produced by [Pi-Hut](https://github.com/ThePiHut/rgbxmastree/). The principal difference is that the [tree.py](/app/tree.py) file in this repo separates the virtual representation of the LED tree on your Pi from the data that is transferred to the tree device.

This implementation is achieved by running a separate thread, which takes a snapshot of the virtual representation of the tree at a set frequency (eg, 120hz). This allows the main thread to freely update the virtual representation, without triggering a new transfer of data. For the Pi-Hut implementation, there was no separation, so updating any values would trigger a transfer of data to the tree.

This allows you to be more flexible in how you mutate the state of the tree. In particular, it makes it more straightforward to implement glow or hue effects in a per-LED basis, with each effect cycle running as an async task and independently mutating state. 

The [app/depr](/app/depr) folder contains some code based on the original Pi-Hut, except that that the main [tree.py](/app/depr/tree.py) has had types added to it (and some of the examples have been tinkered with).

For anyone (like me) who is new to working on a Pi Zero, the dev setup I found worked best was to: (1) connect to Pi Zero via [SSH](https://www.raspberrypi.com/documentation/computers/remote-access.html#ssh); and (2) [establish a Network File System](https://www.raspberrypi.com/documentation/computers/remote-access.html#nfs) - Pi Zero as server, laptop as client. This seemed to be more stable than the other options (particularly VS Code devcontainers, which kept disconnecting - perhaps too much for the Pi Zero).

## Getting started



```bash
# Clone repo
git clone https://github.com/jcorrie/rgbxmastree.git
# Install uv if you don't have this already
curl -LsSf https://astral.sh/uv/install.sh | sh
# Set up venv and install deps 
uv venv
source .venv/bin/activate
uv pip install pyproject.toml
```

## Run examples

```bash
python -m app.examples.disco
```