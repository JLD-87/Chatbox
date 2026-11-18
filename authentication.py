import threading
from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError
)
import json
import os

#absolute path to the users.json file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")

class Auth_class:

    def __init__(self):
        self.create_users_file()
        self.users = self.load_users()
        self.ph = PasswordHasher()
        self.users_lock = threading.Lock()

    # Read json file and return a dictionary of users
    def load_users(self):
        with open(USERS_FILE, "r") as file:
            return json.load(file)

    # Save a json file
    def save_user(self):
        with open(USERS_FILE, "w") as file:
            json.dump(self.users, file, indent=4)

    # Register a new user
    def register_user(self, username, password):

        with self.users_lock:

            if username in self.users:
                print(f"Registration failed: Username '{username}' already exists.")
                return False

            hashed_password = self.ph.hash(password)

            self.users[username] = {
                "password": hashed_password,
                "nickname": username 
            }

            self.save_user()

        return True

    # if user exists, and the password is correct, returns True and the server accepts authentication, a lock prevents race conditions
    def authenticate_user(self, username, password):

        with self.users_lock:

            user = self.users.get(username)

            if user is None:
                return False

            return self.verify_password(password, user["password"])

    # hash and salt the password using argon2
    def hash_password(self, password):
        return self.ph.hash(password)

    # verify the password against the hashed password
    def verify_password(self, password, stored_hash):
        try:
            return self.ph.verify(stored_hash, password)

        except VerificationError:
            return False

    # Creates the users.json file if it doesn't exist
    def create_users_file(self):
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w") as file:
                json.dump({}, file, indent=4)