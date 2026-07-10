from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class EmailOrUsernameAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifiant = username or kwargs.get('email', '')
        if not identifiant or not password:
            return None

        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(
                Q(email__iexact=identifiant) | Q(username=identifiant)
            )
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            try:
                user = UserModel._default_manager.get(username=identifiant)
            except UserModel.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
