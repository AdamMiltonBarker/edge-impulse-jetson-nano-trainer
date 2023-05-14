class project:
    def __init__(self):

        self.id = None
        self.name = None
        self.key = None

    def set_project_id(self, id):
        self.id = id

    def get_project_id(self):
        return self.id

    def set_project_name(self, name):
        self.name = name

    def get_project_name(self):
        return self.name

    def set_project_key(self, key):
        self.key = key

    def get_project_key(self):
        return self.key
