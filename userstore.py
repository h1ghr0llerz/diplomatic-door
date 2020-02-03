import json
import os

class UserStore(object):
    FINGERPRINT_PATH="fingerprint_bmps"
    def __init__(self, path):
        # load store.json
        self._path = path
        try:
            data = json.load(open(os.path.join(path, "store.json")))
        except (json.decoder.JSONDecodeError, OSError) as e:
            print(e)
            return None

        # check keys
        assert 'permitted_user_ids' in data 
        assert 'users' in data
        
        self._permitted_user_ids = data['permitted_user_ids']
        users = {}

        for user in data['users']:
            users[str(user['user_id'])] = DiplomaticUser.load_from_path(
                        os.path.join(path, 
                        user['user_path'])
                    )
        self._users = users

    def get_user(self, user_id):
        return self._users.get(user_id)

    @property
    def permitted_user_ids(self):
        return self._permitted_user_ids

class DiplomaticUser(object):
    FIELDS=['user_id', 'first_name', 'last_name', 'comments', 'fingerprint_bmp']
    def __init__(self, data):
        # initialize all data
        if not all(_ in data for _ in self.FIELDS):
            print("Could not load user.")
            return None
        # store locally
        self._data = data
    
    @classmethod
    def load_from_path(cls, user_dir):
        # load data dictionary
        data = json.load(open(os.path.join(user_dir, "user.json")))
        return cls(data)

    @property
    def _user_directory(self):
        user_dir_format = "%s_%s_%s"
        return user_dir_format % (
                self._data['user_id'],
                self._data['first_name'],
                self._data['last_name']
            )

    @property 
    def first_name(self):
        return self._data['first_name']

    @property 
    def last_name(self):
        return self._data['last_name']

    @property 
    def user_id(self):
        return self._data['user_id']

    @property 
    def comments(self):
        return self._data['comments']

    @property 
    def fingerprint_bmp(self):
        return self._data['fingerprint_bmp']

