from unittest import TestCase

import os
from app import app
from models import db, User
import jwt


# Use test database and don't clutter tests with SQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///sharebnb_test'
app.config['SQLALCHEMY_ECHO'] = False

SECRET_KEY = os.environ['SECRET_KEY']

# Make Flask errors be real errors, rather than HTML pages with error info
app.config['TESTING'] = True

db.drop_all()
db.create_all()

USER_DATA = {
    "username": "TestUsername1",
    "first_name": "TestFirstName1",
    "last_name": "TestLastName1",
    "email": "testEmail1@email.com",
    "password": "password"
}

USER_DATA_2 = {
    "username": "TestUsername2",
    "first_name": "TestSFirstName2",
    "last_name": "TestLastName2",
    "email": "testEmail2@email.com",
    "password": "password"
}


class UserRoutes(TestCase):
    """Tests for views of API."""

    def setUp(self):
        """Make demo data."""

        User.query.delete()

        user = User(**USER_DATA)
        db.session.add(user)
        db.session.commit()

        self.user = user

    def tearDown(self):
        """Clean up fouled transactions."""

        db.session.rollback()

    def test_create_user(self):
        with app.test_client() as client:
            url = "/api/signup"
            resp = client.post(url, json=USER_DATA_2)

            self.assertEqual(resp.status_code, 201)

            data = resp.json.copy()

            decode = jwt.decode(data.get("token"),SECRET_KEY,algorithms=["HS256"])
            self.assertEqual(decode, {'username': 'TestUsername2'})

            self.assertEqual(User.query.count(), 2)

    def test_login_user(self):
        with app.test_client() as client:
            url = "/api/signup"
            resp = client.post(url, json=USER_DATA_2)

            url = "/api/login"
            resp = client.post(url, json={
                                          "username": "TestUsername2",
                                          "password": "password"
                                          })

            self.assertEqual(resp.status_code, 200)
            data = resp.json
            decode = jwt.decode(data.get("token"),SECRET_KEY,algorithms=["HS256"])
            self.assertEqual(decode, {'username': 'TestUsername2'})

    def test_login_user_bad_credentials(self):
        with app.test_client() as client:
            url = "/api/signup"
            resp = client.post(url, json=USER_DATA_2)

            url = "/api/login"
            resp = client.post(url, json={
                                          "username": "TestUsername2",
                                          "password": "badpassword"
                                          })

            self.assertEqual(resp.status_code, 401)
            data = resp.json
            self.assertEqual(data, {"error": "invalid credentials"})


    # def test_update_user(self):
    #     with app.test_client() as client:
    #         url = f"/api/users/{self.user.id}"
    #         resp = client.patch(url, json=user_DATA_2)

    #         self.assertEqual(resp.status_code, 200)

    #         data = resp.json
    #         self.assertEqual(data, {
    #             "user": {
    #                 "id": self.user.id,
    #                 "flavor": "TestFlavor2",
    #                 "size": "TestSize2",
    #                 "rating": 10,
    #                 "image": "http://test.com/user2.jpg"
    #             }
    #         })

    #         self.assertEqual(user.query.count(), 1)

    # def test_update_user_missing(self):
    #     with app.test_client() as client:
    #         url = f"/api/users/99999"
    #         resp = client.patch(url, json=user_DATA_2)

    #         self.assertEqual(resp.status_code, 404)

    # def test_delete_user(self):
    #     with app.test_client() as client:
    #         url = f"/api/users/{self.user.id}"
    #         resp = client.delete(url)

    #         self.assertEqual(resp.status_code, 200)

    #         data = resp.json
    #         self.assertEqual(data, {"deleted": self.user.id})

    #         self.assertEqual(user.query.count(), 0)

    # def test_delete_user_missing(self):
    #     with app.test_client() as client:
    #         url = f"/api/users/99999"
    #         resp = client.delete(url)

    #         self.assertEqual(resp.status_code, 404)
