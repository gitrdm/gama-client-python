import json
from enum import Enum
from json.decoder import JSONObject

import websockets
import asyncio
from typing import List, Dict, Union


class CommandType(Enum):
    LAUNCH      = "launch"
    PLAY        = "play"
    PAUSE       = "pause"
    STEP        = "step"
    STEP_BACK   = "stepBack"
    RELOAD      = "reload"
    STOP        = "stop"
    EXPRESSION  = "expression"


class GamaClient:

    # STATIC METHODS
    @staticmethod
    def create_gama_command(command_type: str, socket_id: str, gaml_file_path: str = "", experiment_name: str = "",
                            exp_id: str = "", end_condition: str = "", params: List[Dict] = None, expression: str = "")\
            -> Dict:
        """
        Function used to create a command to send to gama-server.
        :param command_type:   a string among the enum CommandType, used in every command to know what kind of action
                        must be executed by gama-server.
        :param socket_id:  a string representing the id of a connection to gama-server.
                    This id is given by gama-server directly after connecting to it.
                    It must be transmitted with every command sent to the server.
        :param gaml_file_path: a string representing the path to the gaml file to be run by gama-server
                        (the path must be on the gama-server side)
        :param experiment_name:    a string representing the name of the experiment in the gaml file to be run by gama-server
        :param exp_id: a string representing the id of an experiment currently run by gama-server.
                Used to apply the command to a specific experiment.
        :param end_condition:  a string representing an ending condition to stop an experiment run by gama-server.
                        It must be expressed in the gaml language.
        :param params: a list of dictionaries, each dictionary representing the initial value of an experiment parameter.
                Those parameters would be set at the initialization phase of the experiment.

                The parameters must follow this format:
                {
                    "type": "<type of the parameter>",
                    "value": "<value of the parameter>",
                    "name": "<name of the parameter in the gaml file>"
                }

                Example value of params: [{"type": "float", "value": "0.75", "name": "conversion_rate"}]
        :param expression: a string representing a gaml expression to be executed by gama-server.
        :return:    A dictionary containing all the parameters needed to interact with gama-server, you will still need to send
                    it to gama as a string afterward.
        """
        return {
            "type": command_type,
            "socket_id": socket_id,
            "model": gaml_file_path,
            "experiment": experiment_name,
            "exp_id": exp_id,
            "auto-export": False,
            "parameters": params,
            "until": end_condition,
            "expr": expression,
        }

    # CLASS VARIABLES
    socket:     websockets.WebSocketClientProtocol
    socket_id:  str
    url:        str
    port:       int

    def __init__(self, url: str, port: int):
        """
        Initialize the client. At this point no connection is made yet.
        :param url: a string representing the url (or ip address) where the gama-server is running
        :param port: an integer representing the port on which the server runs
        """
        self.url        = url
        self.port       = port
        self.socket_id  = ""
        self.socket     = None

    async def connect(self):
        """
        Tries to connect the client to gama-server using the url and port given at the initialization.
        Can throw exceptions in case of connection problems
        """
        self.socket     = await websockets.connect(f"ws://{self.url}:{self.port}")
        self.socket_id  = await self.socket.recv()

    async def send_message(self, message: str):
        """
        Send a string to the currently connected gama-server
        :param message:
        """
        await self.socket.send(message)

    async def read_message(self) -> str:
        """
        Reads the next message from gama-server
        :return: a string containing the message
        """
        return await self.socket.recv()

    def open(self) -> bool:
        """
        Checks that the object is currently connected to gama-server with an open socket.
        :return: True if the socket is initialized and currently open
        """
        return self.socket is not None and self.socket.open()

    async def send_command(self, command_type: CommandType, gaml_file_path: str = "", experiment_name: str = "",
                           exp_id: str = "", end_condition: str = "", params: List[Dict] = None, expression: str = ""):
        """
        Sends a command to gama-server through the current connection.
        Only the command_type is mandatory for any call of the method, the other parameters could be required
        depending on the context.
        See GamaClient.create_gama_command for more details.
        :param command_type: the type of command to send, to pick among the values of CommandType
        :param gaml_file_path: the path of the gaml file containing the experiment to run
        :param experiment_name: the name of the experiment to run
        :param exp_id: the id of the experiment on which to run the command
        :param end_condition: the condition which will make gama-server end the simulation (written in gaml)
        :param params: the parameters to set at the initialization of the experiment.
        :param expression: a string representing a gaml expression to be executed by gama-server.
        """
        cmd = self.create_gama_command(str(command_type.value), self.socket_id, gaml_file_path, experiment_name,
                                       exp_id, end_condition, params, expression)
        cmd_to_str = json.dumps(cmd, indent=0)
        await self.socket.send(cmd_to_str)

    async def send_command_return(self, command_type: CommandType, gaml_file_path: str = "", experiment_name: str = "",
                                  exp_id: str = "", end_condition: str = "",
                                  params: List[Dict] = None, expression: str = "", unpack_json: bool = False)\
            -> Union[str, JSONObject]:
        """
        Same as send_command but wait for the answer from gama-server and can convert it to json depending on parameters
        :param command_type: the type of command to send, to pick among the values of CommandType
        :param gaml_file_path: the path of the gaml file containing the experiment to run
        :param experiment_name: the name of the experiment to run
        :param exp_id: the id of the experiment on which to run the command
        :param end_condition: the condition which will make gama-server end the simulation (written in gaml)
        :param params: the parameters to set at the initialization of the experiment.
        :param unpack_json: boolean, if true unpack the answer from gama-server as a json object, else returns the raw text
        :param expression: a string representing a gaml expression to be executed by gama-server.
        :return: the answer from gama-server after receiving the command from the client
        """
        await self.send_command(command_type=command_type,
                                gaml_file_path=gaml_file_path,
                                experiment_name=experiment_name,
                                exp_id=exp_id,
                                end_condition=end_condition,
                                params=params,
                                expression=expression)
        res = await self.socket.recv()
        if unpack_json:
            res = json.loads(res)
        return res

    async def init_experiment(self, gaml_file_path: str, experiment_name: str, params: List[Dict] = None) -> str:
        """
        Loads the experiment experiment_name from the file gaml_file_path (on the server side) and returns the experiment's id
        :param gaml_file_path: the path of the gaml file containing the experiment to run
        :param experiment_name: the name of the experiment to run
        :param params: a list of dictionaries, each dictionary representing the initial value of an experiment parameter.
                    Those parameters would be set at the initialization phase of the experiment.
                    The parameters must follow this format:
                    {
                        "type": "<type of the parameter>",
                        "value": "<value of the parameter>",
                        "name": "<name of the parameter in the gaml file>"
                    }
                    Example value of params: [{"type": "float", "value": "0.75", "name": "conversion_rate"}]
        :return: a string representing the experiment's id. You need it to use other commands on that experiment later (play, pause etc.)
        """
        res = await self.send_command_return(CommandType.LAUNCH,
                                             gaml_file_path=gaml_file_path,
                                             experiment_name=experiment_name,
                                             params=params,
                                             unpack_json=True,
                                             )
        return res["exp_id"]

    async def play(self, experiment_id: str) -> bool:
        """
        Starts the experiment. You must call this function after the experiment's initialization.
        :param experiment_id: a string representing the experiment's id given at the initialization
        :return: True if the command has been executed normally, False otherwise
        """
        res = await self.send_command_return(CommandType.PLAY, exp_id=experiment_id)
        return res == CommandType.PLAY.value

    async def pause(self, experiment_id: str) -> bool:
        """
        Pauses the experiment represented by the parameter experiment_id. You must have called the play or reload function before.
        :param experiment_id: a string representing the experiment's id given at the initialization
        :return: True if the command has been executed normally, False otherwise
        """
        res = await self.send_command_return(CommandType.PAUSE, exp_id=experiment_id)
        return res == CommandType.PAUSE.value

    async def step(self, experiment_id: str) -> bool:
        """
        Executes one (and only one) step of the simulation represented by experiment_id.
        :param experiment_id: a string representing the experiment's id given at the initialization
        :return: True if the command has been executed normally, False otherwise
        """
        res = await self.send_command_return(CommandType.STEP, exp_id=experiment_id)
        return res == CommandType.STEP.value

    async def stepBack(self, experiment_id: str) -> bool:
        """
        Executes one (and only one and only if available) step back on the simulation represented by experiment_id.
        :param experiment_id: a string representing the experiment's id given at the initialization
        :return: True if the command has been executed normally, False otherwise
        """
        res = await self.send_command_return(CommandType.STEP_BACK, exp_id=experiment_id)
        return res == CommandType.STEP_BACK.value

    async def reload(self, experiment_id: str, params: List[Dict] = None) -> bool:
        """
        Reloads the experiment represented by experiment_id. It will stop the current experiment if running, initialize it again with the parameters params given (if any), and start running it.
        :param experiment_id: a string representing the experiment's id given at the initialization
        :param params: a list of dictionaries, each dictionary representing the initial value of an experiment parameter.
                    Those parameters would be set at the initialization phase of the experiment.
                    The parameters must follow this format:
                    {
                        "type": "<type of the parameter>",
                        "value": "<value of the parameter>",
                        "name": "<name of the parameter in the gaml file>"
                    }
                    Example value of params: [{"type": "float", "value": "0.75", "name": "conversion_rate"}]
        :return: True if the command has been executed normally, False otherwise
        """
        res = await self.send_command_return(CommandType.RELOAD, exp_id=experiment_id, params=params)
        return res == CommandType.RELOAD.value

    async def stop(self, experiment_id: str) -> bool:
        """
        Completely stops the experiment represented by experiment_id.
        :param experiment_id: a string representing the experiment's id given at the initialization
        :return: True if the command has been executed normally, False otherwise
        """
        res = await self.send_command_return(CommandType.STOP, exp_id=experiment_id)
        return res == CommandType.STOP.value

    async def expression(self, experiment_id: str, expression: str) -> JSONObject:
        res: JSONObject = await self.send_command_return(CommandType.EXPRESSION,
                                                   exp_id=experiment_id,
                                                   expression=expression,
                                                   unpack_json=True)
        return res["result"]


