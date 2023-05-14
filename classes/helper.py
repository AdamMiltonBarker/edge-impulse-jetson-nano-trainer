import json
import os
import requests


class helper:
    """Helper class"""

    def __init__(self):

        self.load_config()

    def load_config(self):

        with open(
            os.path.dirname(os.path.abspath(__file__)) + "/../confs.json"
        ) as confs:
            self.confs = json.loads(confs.read())

    def write_config(self):

        with open(
            os.path.dirname(os.path.abspath(__file__)) + "/../confs.json", "w"
        ) as confs:
            json.dump(self.confs, confs, indent=4, sort_keys=True)

    def set_new_project(self, project_id, project_name):
        self.confs["project"]["id"] = project_id
        self.confs["project"]["name"] = project_name
        self.write_config()

    def set_project_key(self, key):
        self.confs["project"]["key"] = key
        self.write_config()

    def set_new_device(self, device_id):
        self.confs["device"]["id"] = device_id
        self.write_config()

    def set_data_type(self, data_type):
        self.confs["data"]["type"] = data_type
        self.write_config()

    def set_train_data_complete(self):
        self.confs["data"]["train_data"] = True
        self.write_config()

    def set_test_data_complete(self):
        self.confs["data"]["test_data"] = True
        self.write_config()

    def set_impulse_complete(self):
        self.confs["impulse"]["created"] = True
        self.write_config()

    def set_features_generated(self):
        self.confs["features"]["generated"] = True
        self.write_config()

    def set_trained(self):
        self.confs["model"]["trained"] = True
        self.write_config()

    def set_tested(self):
        self.confs["model"]["tested"] = True
        self.write_config()

    def http_request(self, method, address, headers, jsond=False, files=False):

        if method == "POST":
            if jsond:
                response = requests.post(address, json=jsond, headers=headers)
            elif files:
                response = requests.post(address, files=files, headers=headers)
            else:
                response = requests.post(address, headers=headers)

        elif method == "GET":
            response = requests.get(address, headers=headers)

        response_code = response.status_code
        response_json = json.loads(response.text)

        return response_code, response_json
