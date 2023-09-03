import os
import sys
import yaml
import logging
import logging
import singleton_meta as sm


class LoRa2MQTTConfiguration(metaclass=sm.SingletonMeta):
    CONFIG_FILE_NAME = "/config.yaml"

    def __init__(self):
        super().__init__()
        try:
            # Navigate up the directory tree until you find the project root
            msg = None
            file = os.getcwd() + self.CONFIG_FILE_NAME
            with open(file, "r") as config_file:
                config = yaml.safe_load(config_file)
                self.logging_level = config["log"]["level"]
        except FileNotFoundError as exception:
            msg = "Configuration file not found. Please create a config.yaml file in the project root directory."
        except KeyError as exception:
            msg = f"Missing or invalid configuration: {str(exception)}"
        except Exception as exception:
            msg = f"Error loading configuration: {str(exception)}"
        finally:
            if msg is not None:
                logging.basicConfig(
                    level=logging.INFO,
                    format="%(asctime)s %(message)s",
                    datefmt="%b %d %H:%M:%S",
                )
                logging.info("error in configuration file: %s", file)
                logging.info(msg)
                sys.exit(1)
