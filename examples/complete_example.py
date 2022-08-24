import time
import asyncio
from gama_client.client import GamaClient


async def main():

	MY_SERVER_URL = "localhost"
	MY_SERVER_PORT = 6868
	GAML_FILE_PATH_ON_SERVER = "/opt/gama-platform/headless/samples/predatorPrey/predatorPrey.gaml"
	EXPERIMENT_NAME = "prey_predatorExp"

	client = GamaClient(MY_SERVER_URL, MY_SERVER_PORT)

	print("connecting to Gama server")
	await client.connect()

	print("initialize a gaml model")
	experiment_id = await client.init_experiment(GAML_FILE_PATH_ON_SERVER, EXPERIMENT_NAME, [{"type": "int", "name": "nb_preys_init", "value": 100}])
	if experiment_id == "":
		print("error while initializing")
		return

	print("initialization successful, running the model")
	playing = await client.play(experiment_id)
	if not playing:
		print("error while trying to run the experiment", experiment_id)
		return

	print("model running, waiting a bit")
	time.sleep(3)

	print("pausing the model")
	if not await client.pause(experiment_id):
		print("unable to pause the experiment", experiment_id)
		return

	print("asking simulation the value of: cycle=", await client.expression(experiment_id, r"cycle"))
	print("asking simulation the value of: nb_preys/nb_preys_init=", await client.expression(experiment_id, r"nb_preys/nb_preys_init"))

if __name__ == "__main__":
	asyncio.run(main())
	