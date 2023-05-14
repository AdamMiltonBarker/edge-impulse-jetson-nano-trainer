import os
import pathlib


class data:
    def __init__(self):

        self.type = None

    def set_data_type(self, type):
        self.type = type

    def get_data_type(self):
        return self.type

    def process_data(self, dir, file_type):

        data_list = {}
        for path in pathlib.Path(dir).iterdir():
            if path.is_dir():
                data_list[os.path.basename(path)] = []
                data_list[os.path.basename(path)].append(
                    list(filter(lambda path: path.suffix in file_type, path.glob("*")))
                )
        return data_list
