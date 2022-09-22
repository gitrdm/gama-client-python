# Gama client python
 A python 3 client wrapper for gama-server, the headless version of the modeling platform [gama](https://gama-platform.org/).

# Installation
In your python environment, install the gama-client package with the command:

```
pip install gama-client
```

For advanced users, you can find the package on the [pypi website](https://pypi.org/project/gama-client/) and do it yourself instead of using the `pip` tool.

You can check that everything went well by opening a python console and try the following line:

```
from gama_client.client import GamaClient
```

If you don't see any error message then `gama-client` has been installed correctly.


# Using it

To use `gama-client` you first need to have a [gama-server](https://gama-platform.org/wiki/HeadlessServer) open. Then you can interact with it with the `GamaClient` class.
Currently the available operations are:
 * connecting to gama-server
 * check if the connection is still alive
 * load an experiment on the server (compile + run the `init` block)
 * run an experiment
 * pause an experiment
 * execute one step of the experiment
 * rollback one step of the experiment (when available)
 * reload an experiment
 * stop an experiment
 * ask gama-server to process a gaml expression (having an experiment as context)
 
 A complete working example is given in the `examples` directory, you just have to change the values of the variables `MY_SERVER_URL`, `MY_SERVER_PORT`, `GAML_FILE_PATH_ON_SERVER` and `EXPERIMENT_NAME` to the one corresponding to your own gama-server and experiment to try it.
 
 
