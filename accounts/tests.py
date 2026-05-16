from django.test import TestCase

from .serializers import UserRegistrationSerializer


class UserRegistrationSerializerTests(TestCase):
    def _payload(self, **overrides):
        data = {
            'email': 'new-user@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
        }
        data.update(overrides)
        return data

    def test_registration_accepts_local_us_phone(self):
        serializer = UserRegistrationSerializer(data=self._payload(phone='4155552671'))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(str(user.phone), '+14155552671')

    def test_registration_accepts_formatted_phone(self):
        serializer = UserRegistrationSerializer(data=self._payload(
            email='formatted@example.com',
            phone='(415) 555-2671'
        ))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(str(user.phone), '+14155552671')

    def test_registration_allows_blank_phone(self):
        serializer = UserRegistrationSerializer(data=self._payload(
            email='blank@example.com',
            phone=''
        ))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertIsNone(user.phone)
