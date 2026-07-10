from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import Utilisateur, HistoriqueAction

admin.site.unregister(Group)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Utilisateur


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = Utilisateur

    list_display = ('username', 'email', 'telephone_mobile', 'statut', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('statut', 'is_active', 'is_staff', 'groups')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {'fields': (
            'first_name', 'last_name', 'email', 'telephone_mobile', 'photo_profil', 'porte_entree'
        )}),
        ('Statut', {'fields': ('statut', 'is_active', 'is_staff', 'is_superuser')}),
        ('Groupes & Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


@admin.register(Group)
class CustomGroupAdmin(GroupAdmin):
    list_display = ('name',)


@admin.register(HistoriqueAction)
class HistoriqueActionAdmin(admin.ModelAdmin):
    list_display = ('action', 'entite', 'utilisateur', 'created_at')
    search_fields = ('action', 'entite', 'details')
    list_filter = ('action', 'entite', 'created_at')
    readonly_fields = ('uuid', 'created_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('utilisateur')
