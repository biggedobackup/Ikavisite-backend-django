from django import template

register = template.Library()


@register.simple_tag
def user_role(user):
    """
    Retourne le libellé du rôle d'un utilisateur.
    Priorité : Groupes > superuser > staff > utilisateur simple.
    """
    groups = user.groups.all()
    if groups:
        return groups[0].name
    if user.is_superuser:
        return "Super administrateur"
    if user.is_staff:
        return "Staff"
    return "Utilisateur"
