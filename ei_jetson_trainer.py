import getpass
import json
import os
import re
import threading
import websocket

from classes.helper import helper
from classes.user import user
from classes.project import project
from classes.device import device
from classes.data import data


class EdgeImpulseJetsonNanoTrainer:
    def __init__(self):
        self.helper = helper()
        self.user = user()
        self.project = project()
        self.device = device()
        self.data = data()

        self.ws = None
        self.wskey = None
        self.wsexpiry = None

        self.feature_job = None
        self.features_complete = False

        self.train_job = None
        self.train_complete = False

        self.test_job = None
        self.test_complete = False

    def set_socket_key(self, key):
        self.wskey = key

    def get_socket_key(self):
        return self.wskey

    def set_socket_expiry(self, expiry):
        self.wsexpiry = expiry

    def get_socket_expiry(self):
        return self.wsexpiry

    def keepalive(self):
        self.ws.send("2")
        threading.Timer(20.0, self.keepalive).start()

    def on_open(self, ws):
        threading.Timer(20.0, self.keepalive).start()

    def on_message(self, ws, message):
        def run(message):
            message = re.sub("^\d+", "", message)
            if message == None or message == "":
                return
            message = json.loads(message)
            if (
                isinstance(message, list)
                and message[0] not in self.helper.confs["socket"]["ignore"]
            ):
                if (
                    not self.features_complete
                    and self.feature_job != None
                    and message[0] == "job-finished-" + str(self.feature_job)
                ):
                    print("** FEATURES COMPLETE")
                    self.features_complete = True
                if (
                    not self.train_complete
                    and self.train_job != None
                    and message[0] == "job-finished-" + str(self.train_job)
                ):
                    print("** TRAIN COMPLETE")
                    self.train_complete = True
                if (
                    not self.test_complete
                    and self.test_job != None
                    and message[0] == "job-finished-" + str(self.test_job)
                ):
                    print("** TEST COMPLETE")
                    self.test_complete = True
            if (
                self.helper.confs["socket"]["debug"]
                and message[0] not in self.helper.confs["socket"]["ignore"]
            ):
                print(message)

        threading.Thread(target=run, args=(message,)).start()

    def on_close(self, ws):
        print("** SOCKET CLOSED")

    def connect(self):
        url = (
            "wss://studio.edgeimpulse.com/socket.io/?token="
            + self.get_socket_key()
            + "&EIO=3&transport=websocket"
        )
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close,
        )
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def login(self):
        username = input("What is your username?\n")
        password = getpass.getpass("What is your password?\n")

        resp_code, resp = self.helper.http_request(
            "POST", self.helper.confs["urls"]["login"],
            {"content-type": "application/json"},
            {"username": username, "password": password},
        )
        if resp_code == 200:
            self.user.set_username(username)
            self.user.set_cookie(resp["token"])
        else:
            self.login()

    def project_init(self):
        if self.helper.confs["project"]["name"]:
            self.project.set_project_id(self.helper.confs["project"]["id"])
            self.project.set_project_name(self.helper.confs["project"]["name"])
            print(
                "** Working on project id {0} {1}".format(
                    str(self.project.get_project_id()), self.project.get_project_name()
                )
            )
            return

        project_name = input("What is your new project name?\n")

        resp_code, resp = self.helper.http_request(
            "POST", self.helper.confs["urls"]["project_create"],
            {"content-type": "application/json", "x-jwt-token": self.user.get_cookie()},
            {"projectName": project_name},
        )
        if resp_code == 200:
            self.helper.set_new_project(resp["id"], project_name)
            self.project.set_project_id(resp["id"])
            self.project.set_project_name(project_name)
        else:
            print("** There was an error with your request, please try again!")
            self.project_init()

    def project_key(self):
        if self.helper.confs["project"]["key"]:
            self.project.set_project_key(self.helper.confs["project"]["key"])
            return

        url = self.helper.confs["urls"]["project_key_create"].replace(
            "{projectId}", str(self.project.get_project_id())
        )

        resp_code, resp = self.helper.http_request(
            "GET", url,
            {"content-type": "application/json", "x-jwt-token": self.user.get_cookie()},
        )
        if resp_code == 200 and resp["success"] is not False:
            for key in resp["apiKeys"]:
                if key["isDevelopmentKey"] == True:
                    self.project.set_project_key(key["apiKey"])
                    self.helper.set_project_key(key["apiKey"])
                    print("** API key set")
                    return
        else:
            raise Exception("Cannot retrieve API key")

    def start_socket(self):

        url = self.helper.confs["urls"]["get_websocket_key"].replace(
            "{projectId}", str(self.project.get_project_id())
        )

        resp_code, resp = self.helper.http_request(
            "GET", url,
            {"x-jwt-token": self.user.get_cookie()},
        )
        if resp_code == 200 and resp["success"] is not False:
            self.set_socket_key(resp["token"]["socketToken"])
            self.set_socket_expiry(resp["token"]["expires"])
        else:
            raise Exception("Cannot retrieve socket key")

        self.connect()

    def device_init(self):
        if self.helper.confs["device"]["id"]:
            self.device.set_device_id(self.helper.confs["device"]["id"])

            print("** Working on device id {0}".format(self.device.get_device_id()))

            print(
                "** Follow the guide at {0} to connect your device".format(
                    self.helper.confs["urls"]["device_connect_doc"]
                )
            )
            return

        print(
            "** Follow the guide at {0}".format(
                self.helper.confs["urls"]["device_connect_doc"]
            )
        )
        device_id = input("What is your new device ID?\n")

        url = (
            self.helper.confs["urls"]["get_device"]
            .replace("{projectId}", str(self.project.get_project_id()))
            .replace("{deviceId}", str(device_id).lower())
        )

        resp_code, resp = self.helper.http_request(
            "GET", url, {"x-jwt-token": self.user.get_cookie()}
        )
        if resp_code == 200 and resp["success"] is not False:
            self.helper.set_new_device(resp["device"]["deviceId"])
            self.device.set_device_id(resp["device"]["deviceId"])
        else:
            print("** There was an error with your request, please try again!")
            self.device_init()

    def data_init(self):
        if self.helper.confs["data"]["type"]:
            self.data.set_data_type(self.helper.confs["data"]["type"])
            print("** Data ingestion type is {0}".format(self.data.get_data_type()))
            return

        data_type = input("What is your new data ingestion type? (local or remote)\n")
        if data_type not in self.helper.confs["data"]["types"]:
            self.data_init()

        self.helper.set_data_type(data_type)
        self.data.set_data_type(data_type)
        print("** Data ingestion type is {0}".format(self.data.get_data_type()))

    def data_prepare(self):
        if (
            self.helper.confs["data"]["type"] == "local"
            and self.helper.confs["data"]["train_data"] == False
            and self.helper.confs["data"]["test_data"] == False
        ):
            print("** Make sure your data is in the data/train and data/test folders.")
            print("** Directory names in these folders will be used as the labels.")
            train_data = self.data.process_data(
                self.helper.confs["data"]["train_dir"],
                self.helper.confs["data"]["file_type"],
            )
            if not len(train_data):
                raise Exception("** Check your data")
            test_data = self.data.process_data(
                self.helper.confs["data"]["test_dir"],
                self.helper.confs["data"]["file_type"],
            )
            if not len(test_data):
                raise Exception("** Check your data")

            data_types = ["train", "test"]

            for data_type in data_types:
                current = (
                    train_data.items() if data_type == "train" else test_data.items()
                )
                for label, data in current:
                    print(
                        "** {0} {1} {2} data images".format(
                            str(len(data[0])), str(label), data_type
                        )
                    )
                    headers = {
                        "x-label": str(label),
                        "x-api-key": self.project.get_project_key(),
                    }
                    resp_code, resp = self.helper.http_request(
                        "POST",
                        self.helper.confs["urls"][data_type + "_data_ingestion"],
                        headers,
                        False,
                        (
                            ("data", (os.path.basename(i), open(i, "rb"), "image/jpg"))
                            for i in data[0]
                        ),
                    )
                    if resp_code == 200 and resp["success"] is not False:
                        if data_type == "train":
                            self.helper.set_train_data_complete()
                        else:
                            self.helper.set_test_data_complete()
                    else:
                        print(
                            "** There was an error with your request, please try again!"
                        )
                        self.data_prepare()
            return
        if self.helper.confs["data"]["type"] == "remote":
            print(
                "** Head over to the data aquisition tab for your project ({0}). When you have retrieved all of your data type continue below.".format(
                    self.helper.confs["urls"]["platform_ingestion"]
                )
            )
            ready = input("Enter 'Continue' to continue?\n")
            if ready == "Continue" or ready == "continue":
                self.helper.set_train_data_complete()
                self.helper.set_test_data_complete()
            else:
                print("** There was an error with your request, please try again!")
                self.data_prepare()
            return

    def create_impulse(self):
        if self.helper.confs["impulse"]["created"] == False:

            url = self.helper.confs["urls"]["create_impulse"].replace(
                "{projectId}", str(self.project.get_project_id())
            )

            resp_code, resp = self.helper.http_request(
                "POST",
                url,
                {
                    "content-type": "application/json",
                    "x-jwt-token": self.user.get_cookie(),
                },
                self.helper.confs["impulse"]["data"],
            )
            if resp_code == 200 and resp["success"] is not False:
                self.helper.set_impulse_complete()
                self.helper.set_impulse_complete()
            else:
                raise Exception("** There was an error with your request")

    def generate_features(self):
        if self.helper.confs["features"]["generated"] == False:

            url = self.helper.confs["urls"]["generate_features"].replace(
                "{projectId}", str(self.project.get_project_id())
            )

            resp_code, resp = self.helper.http_request(
                "POST",
                url,
                {
                    "content-type": "application/json",
                    "x-jwt-token": self.user.get_cookie(),
                },
                {
                    "dspId": 2,
                    "calculateFeatureImportance": True,
                    "skipFeatureExplorer": True,
                },
            )
            if resp_code == 200 and resp["success"] is not False:
                self.feature_job = resp["id"]
                print("** WAITING FOR FEATURES")
                while not self.features_complete:
                    pass
                self.helper.set_features_generated()
            else:
                raise Exception("** There was an error with your request")

    def train(self):
        if self.helper.confs["model"]["trained"] == False:

            url = (
                self.helper.confs["urls"]["train"]
                .replace("{projectId}", str(self.project.get_project_id()))
                .replace("{learnId}", str(3))
            )

            resp_code, resp = self.helper.http_request(
                "POST",
                url,
                {
                    "content-type": "application/json",
                    "x-jwt-token": self.user.get_cookie(),
                },
                self.helper.confs["model"]["train"],
            )
            if resp_code == 200 and resp["success"] is not False:
                self.train_job = resp["id"]
                print("** WAITING FOR TRAINING")
                while not self.train_complete:
                    pass
                self.helper.set_trained()
            else:
                raise Exception("** There was an error with your request")

    def test(self):
        if self.helper.confs["model"]["tested"] == False:

            url = self.helper.confs["urls"]["test"].replace(
                "{projectId}", str(self.project.get_project_id())
            )
            resp_code, resp = self.helper.http_request(
                "POST", url, {"x-jwt-token": self.user.get_cookie()}
            )
            if resp_code == 200 and resp["success"] is not False:
                self.test_job = resp["id"]
                print("** WAITING FOR TESTING")
                while not self.test_complete:
                    pass
                self.helper.set_tested()
                print("** SETUP COMPLETE, RUN YOUR MODEL BY ENTERING edge-impulse-linux-runner IN TERMINAL")
            else:
                raise Exception("** There was an error with your request")

    def startup(self):

        app_stages = [
            self.login,
            self.project_init,
            self.project_key,
            self.start_socket,
            self.device_init,
            self.data_init,
            self.data_prepare,
            self.create_impulse,
            self.generate_features,
            self.train,
            self.test,
        ]

        for app_stage in app_stages:
            app_stage()


eijnt = EdgeImpulseJetsonNanoTrainer()


def main():
    try:
        eijnt.startup()
    except KeyboardInterrupt:
        print("Exiting")


if __name__ == "__main__":
    main()
