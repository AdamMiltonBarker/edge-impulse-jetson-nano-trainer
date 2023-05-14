class user:
    def __init__(self):

        self.logged_in = False
        self.cookie = None
        self.user_name = None

    def is_logged_in(self):
        return self.logged_in

    def set_cookie(self, cookie):
        self.cookie = cookie

    def get_cookie(self):
        return self.cookie

    def set_username(self, username):
        self.username = username

    def get_username(self):
        return self.username
